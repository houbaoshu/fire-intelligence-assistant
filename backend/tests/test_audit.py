"""审计日志测试：记录创建、定稿、文档下载均落 audit_logs（ARCHITECTURE.md §18.1）。"""

from app.db import SessionLocal
from app.models.user import AuditLog

from .helpers import auth_headers, generate_inspection, make_role, register, wait_task


def _audit_actions() -> list[str]:
    session = SessionLocal()
    try:
        return [a.action for a in session.query(AuditLog).all()]
    finally:
        session.close()


def test_create_finalize_download_audited(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)

    record_id = client.get(
        "/api/inspection-record", headers=auth_headers(tokens)
    ).json()["items"][0]["id"]
    client.put(
        f"/api/inspection-record/{record_id}",
        headers=auth_headers(tokens),
        json={"title": "t"},
    )
    client.get(f"/api/inspection-record/{record_id}/download", headers=auth_headers(tokens))
    # 定稿需 record.finalize 权限（M6：supervisor/admin）
    make_role(tokens["user"]["id"], "supervisor")
    client.put(
        f"/api/inspection-record/{record_id}",
        headers=auth_headers(tokens),
        json={"status": "finalized"},
    )

    actions = _audit_actions()
    assert "inspection_record.create" in actions
    assert "document.download" in actions
    assert "inspection_record.finalize" in actions
