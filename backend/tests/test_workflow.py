"""M5 workflow features: idempotency, retry limits, task center API."""
from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import TaskStateConflictError
from app.models.user import User
from app.services.tasks.task_service import TaskService


def _user(db) -> User:
    from app.core.security import hash_password

    u = User(email=f"w{uuid.uuid4().hex[:8]}@test.com", password_hash=hash_password("x"), role="inspector")
    db.add(u)
    db.flush()
    return u


def test_idempotency_returns_same_task(db):
    u = _user(db)
    svc = TaskService(db)
    key = "gen-key-1"
    t1 = svc.create_task("inspection_record_generation", u.id, input_data={"a": 1}, idempotency_key=key)
    db.flush()
    t2 = svc.create_task("inspection_record_generation", u.id, input_data={"a": 2}, idempotency_key=key)
    db.flush()
    assert t1.id == t2.id
    db.rollback()


def test_retry_creates_new_instance_and_limits(db):
    from app.core.config import get_settings

    u = _user(db)
    svc = TaskService(db)
    max_r = get_settings().TASK_MAX_RETRIES

    # build a chain: original + max_retries retries
    task = svc.create_task("document_generation", u.id, input_data={}, enqueue=False)
    db.flush()
    prev = task
    for _ in range(max_r):
        svc.mark_failed(prev.id, "E", "fail")
        db.flush()
        prev = svc.retry(prev.id)
        db.flush()

    # one more retry must be rejected
    svc.mark_failed(prev.id, "E", "fail")
    db.flush()
    with pytest.raises(TaskStateConflictError):
        svc.retry(prev.id)
    db.rollback()


def test_stale_recovery_requeues(db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.models.task import AiTask

    u = _user(db)
    svc = TaskService(db)
    task = svc.create_task("speech_transcription", u.id, input_data={}, enqueue=False)
    task.status = "processing"
    task.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.flush()
    db.commit()

    from app.core.database import SessionLocal
    from app.services.tasks.worker import TaskWorker

    # worker recovery requeues the stale task (attempt < max retries)
    worker = TaskWorker(session_factory=SessionLocal)
    worker._recover_stale_tasks()

    from sqlalchemy import select as sel

    fresh = SessionLocal()
    try:
        reloaded = fresh.scalar(sel(AiTask).where(AiTask.id == task.id))
        assert reloaded is not None
        assert reloaded.status == "queued"
    finally:
        fresh.close()
    db.rollback()
