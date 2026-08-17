"""知识库端点测试：权限、上传、checksum 去重、删除联动、重建、聚合计数、审计。"""

import uuid

from tests.helpers import auth_headers, fake_embed, make_admin, register, wait_task

REGULATION_TXT = (
    "中华人民共和国消防法\n\n第一章 总则\n\n"
    "第一条 为了预防火灾和减少火灾危害，加强应急救援工作，制定本法。\n\n"
    "第二十八条 任何单位、个人不得损坏、挪用或者擅自拆除、停用消防设施、器材，"
    "不得占用、堵塞、封闭疏散通道、安全出口、消防车通道。"
)


def _register_admin(client):
    tokens = register(client, "admin@example.com")
    make_admin(tokens["user"]["id"])
    return tokens


def _upload(client, tokens, content=REGULATION_TXT, filename="fire-law.txt"):
    return client.post(
        "/api/knowledge/documents",
        headers=auth_headers(tokens),
        files={"file": (filename, content.encode("utf-8"), "text/plain")},
    )


def test_upload_requires_admin(client):
    tokens = register(client)  # 默认角色非 admin
    resp = _upload(client, tokens)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_upload_rejects_bad_extension(client):
    tokens = _register_admin(client)
    resp = client.post(
        "/api/knowledge/documents",
        headers=auth_headers(tokens),
        files={"file": ("evil.exe", b"MZ" + b"\x00" * 32, "application/x-msdownload")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_index_task_fails_readably_without_ai_config(client):
    tokens = _register_admin(client)
    resp = _upload(client, tokens)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    task = wait_task(client, tokens, body["task_id"])
    assert task["status"] == "failed"
    assert task["error_code"] == "AI_SERVICE_NOT_CONFIGURED"
    assert "配置" in task["error_message"]
    # 文档状态同步为 failed，且出现在列表中
    docs = client.get("/api/knowledge/documents", headers=auth_headers(tokens)).json()
    assert docs["total"] == 1
    assert docs["items"][0]["status"] == "failed"
    # 索引 job 落库为 failed 且带可读错误
    from app.db import SessionLocal
    from app.models.knowledge import KnowledgeIndexJob

    session = SessionLocal()
    try:
        job = session.query(KnowledgeIndexJob).filter_by(ai_task_id=uuid.UUID(body["task_id"])).one()
        assert job.status == "failed"
        assert job.action == "index"
        assert job.error_message
    finally:
        session.close()


def test_upload_duplicate_checksum_conflict(client, monkeypatch):
    from app.services.ai.embedding import EmbeddingService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: fake_embed(texts))
    tokens = _register_admin(client)
    first = _upload(client, tokens)
    assert first.status_code == 200
    second = _upload(client, tokens)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DOCUMENT_DUPLICATE"


def test_index_pipeline_e2e(client, monkeypatch):
    from app.services.ai.embedding import EmbeddingService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: fake_embed(texts))
    tokens = _register_admin(client)
    body = _upload(client, tokens).json()
    task = wait_task(client, tokens, body["task_id"])
    assert task["status"] == "completed"
    assert task["result_data"]["document_id"] == body["document_id"]

    docs = client.get("/api/knowledge/documents", headers=auth_headers(tokens)).json()
    item = docs["items"][0]
    assert item["status"] == "indexed"
    assert item["chunk_count"] >= 2  # 序言 + 条文
    assert item["title"] == "fire-law"

    status = client.get("/api/knowledge/status", headers=auth_headers(tokens)).json()
    assert status["document_count"] == 1
    assert status["indexed_count"] == 1
    assert status["indexing_count"] == 0
    assert status["failed_count"] == 0
    assert status["last_indexed_at"] is not None

    # 向量库确有该文档 chunk
    from app.rag.embedding.store import get_vector_store

    assert str(body["document_id"]) in get_vector_store().list_document_ids()


def test_delete_removes_index_and_audits(client, monkeypatch):
    from app.services.ai.embedding import EmbeddingService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: fake_embed(texts))
    tokens = _register_admin(client)
    body = _upload(client, tokens).json()
    wait_task(client, tokens, body["task_id"])

    resp = client.delete(
        f"/api/knowledge/documents/{body['document_id']}", headers=auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": body["document_id"], "deleted": True}

    # 列表不再出现；向量索引已移除
    docs = client.get("/api/knowledge/documents", headers=auth_headers(tokens)).json()
    assert docs["total"] == 0
    from app.rag.embedding.store import get_vector_store

    assert str(body["document_id"]) not in get_vector_store().list_document_ids()

    # delete_index job 与两条审计（upload/delete）
    import sqlalchemy as sa

    from app.db import SessionLocal
    from app.models.knowledge import KnowledgeIndexJob
    from app.models.user import AuditLog

    session = SessionLocal()
    try:
        job = session.query(KnowledgeIndexJob).filter_by(
            knowledge_document_id=uuid.UUID(body["document_id"]), action="delete_index"
        ).one()
        assert job.status == "completed"
        actions = [
            a
            for (a,) in session.execute(
                sa.select(AuditLog.action).where(
                    AuditLog.entity_id == uuid.UUID(body["document_id"])
                )
            )
        ]
        assert "knowledge_document.upload" in actions
        assert "knowledge_document.delete" in actions
    finally:
        session.close()


def test_delete_not_found(client):
    tokens = _register_admin(client)
    resp = client.delete(
        f"/api/knowledge/documents/{uuid.uuid4()}", headers=auth_headers(tokens)
    )
    assert resp.status_code == 404


def test_rebuild_creates_task(client, monkeypatch):
    from app.services.ai.embedding import EmbeddingService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: fake_embed(texts))
    tokens = _register_admin(client)
    body = _upload(client, tokens).json()
    wait_task(client, tokens, body["task_id"])

    resp = client.post("/api/knowledge/rebuild", headers=auth_headers(tokens))
    assert resp.status_code == 200
    task = wait_task(client, tokens, resp.json()["task_id"])
    assert task["status"] == "completed"
    assert task["task_type"] == "knowledge_reindexing"
    assert task["result_data"]["document_count"] == 1

    # 重建不产生重复 chunk
    from app.rag.embedding.store import get_vector_store

    docs = client.get("/api/knowledge/documents", headers=auth_headers(tokens)).json()
    assert docs["items"][0]["chunk_count"] == _count_chunks(body["document_id"])


def _count_chunks(document_id: str) -> int:
    from app.rag.embedding.store import get_vector_store

    store = get_vector_store()
    return sum(1 for _ in store.list_document_ids() if _ == document_id) and len(
        store.search([1.0] + [0.0] * 15, top_k=1000)
    )


def test_rebuild_conflict_when_running(client):
    tokens = _register_admin(client)
    from app.db import SessionLocal
    from app.models.ai_task import AITask

    session = SessionLocal()
    try:
        session.add(
            AITask(
                task_type="knowledge_reindexing",
                status="pending",
                input_data={},
                created_by=uuid.UUID(tokens["user"]["id"]),
            )
        )
        session.commit()
    finally:
        session.close()
    resp = client.post("/api/knowledge/rebuild", headers=auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_rebuild_requires_admin(client):
    tokens = register(client)
    resp = client.post("/api/knowledge/rebuild", headers=auth_headers(tokens))
    assert resp.status_code == 403


def test_status_empty(client):
    tokens = register(client)
    resp = client.get("/api/knowledge/status", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.json() == {
        "document_count": 0,
        "indexed_count": 0,
        "indexing_count": 0,
        "failed_count": 0,
        "last_indexed_at": None,
    }


def test_status_filter(client):
    tokens = _register_admin(client)
    _upload(client, tokens)
    docs = client.get(
        "/api/knowledge/documents?status=indexed", headers=auth_headers(tokens)
    ).json()
    assert docs["total"] == 0
    docs = client.get(
        "/api/knowledge/documents?status=failed", headers=auth_headers(tokens)
    )
    assert docs.status_code == 200


def test_statistics_knowledge_counts(client, monkeypatch):
    from app.services.ai.embedding import EmbeddingService

    monkeypatch.setattr(EmbeddingService, "embed", lambda self, texts: fake_embed(texts))
    tokens = _register_admin(client)
    body = _upload(client, tokens).json()
    wait_task(client, tokens, body["task_id"])
    stats = client.get("/api/statistics", headers=auth_headers(tokens)).json()
    assert stats["knowledge"]["document_count"] == 1
    assert stats["knowledge"]["indexed_count"] == 1
    assert stats["knowledge"]["failed_count"] == 0
