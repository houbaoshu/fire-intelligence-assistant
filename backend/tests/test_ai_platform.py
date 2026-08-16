"""Milestone 8: AI platform (prompts, models, routing, plugins, evaluation)."""
from __future__ import annotations

import uuid

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.services.aiplatform.prompt_service import PromptService
from app.services.aiplatform.router import resolve_model


def _admin(db):
    u = User(email=f"ai-{uuid.uuid4().hex[:8]}@test.com", password_hash=hash_password("password123"), role="admin")
    db.add(u)
    db.commit()
    return u


def _hdrs(u):
    return {"Authorization": "Bearer " + create_access_token(str(u.id))}


def test_prompt_catalog_seeded_and_versioned(client, db):
    from app.models.aiplatform import PromptVersion

    admin = _admin(db)
    PromptService(db).ensure_seeded()
    db.commit()
    hdrs = _hdrs(admin)

    r = client.get("/api/ai-platform/prompts", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["total"] > 0
    qa_prompts = [p for p in r.json()["items"] if p["key"] == "qa.QA_SYSTEM"]
    assert len(qa_prompts) == 1
    prompt_id = qa_prompts[0]["id"]

    # update creates a new version and deactivates the old
    r = client.put(f"/api/ai-platform/prompts/{prompt_id}", headers=hdrs, json={"content": "新版系统提示词"})
    assert r.status_code == 200
    assert r.json()["version"] == 2

    from sqlalchemy import select

    versions = list(db.scalars(select(PromptVersion).where(PromptVersion.key == "qa.QA_SYSTEM")).all())
    assert len(versions) == 2
    active = [v for v in versions if v.is_active]
    assert len(active) == 1
    assert active[0].content == "新版系统提示词"


def test_model_configuration_and_routing(client, db):
    resolve_model.cache_clear()
    admin = _admin(db)
    hdrs = _hdrs(admin)

    r = client.post(
        "/api/ai-platform/models", headers=hdrs,
        json={"name": "DeepSeek R1", "kind": "llm", "model_name": "deepseek-reasoner", "priority": 1},
    )
    assert r.status_code == 201, r.text
    cfg_id = r.json()["id"]

    r = client.post(f"/api/ai-platform/models/{cfg_id}/activate", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["is_active"] is True

    resolve_model.cache_clear()
    assert resolve_model("llm") == "deepseek-reasoner"

    r = client.delete(f"/api/ai-platform/models/{cfg_id}", headers=hdrs)
    assert r.status_code == 200

    resolve_model.cache_clear()
    assert resolve_model("llm") is None  # no DB config; env not set in tests


def test_plugin_registry_discovery_and_hook(db):
    from app.services.aiplatform.plugin_service import get_registry

    plugins = get_registry().discover()
    assert any(p.get("name") == "qa_grounding_note" for p in plugins)

    payload = {"answer": "根据消防法...", "sources": []}
    out = get_registry().run_hook("qa_post_process", dict(payload))
    assert "不构成法律意见" in out["answer"]


def test_plugin_sync_records(client, db):
    from app.models.aiplatform import PluginRecord

    admin = _admin(db)
    hdrs = _hdrs(admin)
    r = client.get("/api/ai-platform/plugins", headers=hdrs)
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1
    assert len(db.query(PluginRecord).all()) >= 1


def test_evaluation_with_mocked_ai(client, db, fake_ai):
    from app.core.database import SessionLocal
    from app.models.aiplatform import EvaluationResult
    from app.models.knowledge import KnowledgeDocument
    from app.services.tasks.registry import TaskContext

    # seed a knowledge document and index it (real pipeline with mocked provider)
    from app.models.user import User

    from app.core.security import hash_password

    u = User(email="kb-owner@test.com", password_hash=hash_password("password123"), role="admin")
    db.add(u)
    db.flush()

    from app.services.file_service import FileService
    from app.services.handlers.knowledge_handler import handle_knowledge_indexing
    from app.services.tasks.task_service import TaskService

    content = "第二十八条 任何单位、个人不得损坏、挪用或者擅自拆除、停用消防设施、器材,不得埋压、圈占、遮挡消火栓或者占用防火间距,不得占用、堵塞、封闭疏散通道、安全出口。"
    fs = FileService(db)
    uf = fs.store_bytes(content.encode("utf-8"), "knowledge_source", "fire_law.txt", u.id, mime="text/plain")
    doc = KnowledgeDocument(
        title="中华人民共和国消防法",
        document_type="regulation",
        status="uploaded",
        uploaded_file_id=uf.id,
        checksum="abc123",
        created_by=u.id,
    )
    db.add(doc)
    db.flush()
    doc_id = doc.id
    db.commit()
    task = TaskService(db).create_task("knowledge_indexing", u.id, input_data={"document_id": str(doc_id)})
    db.commit()
    ctx = TaskContext(
        task_id=task.id, task_type="knowledge_indexing",
        user_id=u.id, input_data={"document_id": str(doc_id)}, db=db, attempt=1,
    )
    handle_knowledge_indexing(ctx)
    db.commit()
    db.refresh(doc)
    assert doc.status == "indexed", (doc.doc_metadata or {}).get("last_error", "unknown")

    admin = _admin(db)
    hdrs = _hdrs(admin)
    r = client.post(
        "/api/ai-platform/evaluations/run", headers=hdrs,
        json={"name": "smoke", "questions": ["安全出口被锁闭适用哪些规定?"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_questions"] == 1
    assert body["passed"] == 1, body["details"]
    assert len(db.query(EvaluationResult).all()) == 1
