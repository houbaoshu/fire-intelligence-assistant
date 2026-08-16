"""Task state machine, retry and cancel tests (specs/workflow.md, API.md §8)."""
from __future__ import annotations

import uuid

from app.models.task import AiTask
from app.services.tasks.task_service import TaskService
from app.core.exceptions import TaskStateConflictError


def _user_id(db):
    from app.models.user import User

    from app.core.security import hash_password

    u = User(email=f"u{uuid.uuid4()}@test.com", password_hash=hash_password("password123"), role="inspector")
    db.add(u)
    db.flush()
    return u


def test_task_lifecycle_via_api(client, auth_headers, admin_headers, db):
    hdrs, user = auth_headers()
    admin_hdrs, _ = admin_headers
    # no tasks yet
    r = client.get("/api/tasks", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    # create a task directly through the service (as if by a business flow)
    u = _user_id(db)
    db.commit()
    task = TaskService(db).create_task("speech_transcription", u.id, input_data={"k": "v"})
    task_id = str(task.id)
    db.commit()

    r = client.get(f"/api/tasks/{task_id}", headers=hdrs)
    assert r.status_code == 404  # different user -> not visible

    r = client.get(f"/api/tasks/{task_id}", headers=admin_hdrs)
    assert r.status_code == 200


def test_retry_cancel_state_rules(db):
    u = _user_id(db)
    svc = TaskService(db)

    # cancel only from pending/queued/processing
    t = svc.create_task("document_generation", u.id, input_data={}, enqueue=False)
    db.flush()
    cancelled = svc.cancel(t.id)
    assert cancelled.status == "cancelled"
    db.flush()
    try:
        svc.cancel(t.id)
        assert False, "cancelling a cancelled task must conflict"
    except TaskStateConflictError:
        pass

    # retry only failed/cancelled
    t2 = svc.create_task("knowledge_indexing", u.id, input_data={}, enqueue=False)
    db.flush()
    try:
        svc.retry(t2.id)
        assert False, "retrying a pending task must conflict"
    except TaskStateConflictError:
        pass
    db.rollback()

    t3 = svc.create_task("knowledge_indexing", u.id, input_data={"d": "1"}, enqueue=False)
    svc.mark_failed(t3.id, "E1", "boom")
    db.flush()
    new_task = svc.retry(t3.id)
    assert new_task.parent_task_id == t3.id
    assert new_task.status == "queued"
    assert new_task.input_data == {"d": "1"}
    db.rollback()


def test_mark_completed_sets_result(db):
    u = _user_id(db)
    svc = TaskService(db)
    t = svc.create_task("document_generation", u.id, input_data={}, enqueue=False)
    db.flush()
    svc.update_progress(t.id, 50, "rendering")
    db.flush()
    svc.mark_completed(t.id, {"record_id": str(uuid.uuid4())})
    db.flush()
    db.refresh(t)
    assert t.status == "completed"
    assert t.progress == 100
    assert t.result_data
    db.rollback()
