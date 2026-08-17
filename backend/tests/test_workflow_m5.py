"""M5 工作流强化测试：转移表、幂等提交、重试上限/死信、reaper、通知、并发。"""

import threading
import time
import uuid
from datetime import timedelta

import pytest

from app.core.exceptions import AppException
from app.db import SessionLocal
from app.models.ai_task import AITask
from app.models.base import utc_now
from app.models.notification import Notification
from app.models.user import AuditLog
from app.services.tasks.executor import InProcessTaskExecutor
from app.services.tasks.reaper import recover_stale_tasks
from app.services.tasks.state_machine import transition

from .helpers import auth_headers, generate_inspection, make_admin, register, wait_task


def _db():
    return SessionLocal()


# ---------- 1. 转移表 ----------


def test_transition_map_rejects_illegal_transitions():
    """非法转移一律 TASK_STATE_CONFLICT；终态无出边；processing→pending 仅 reaper。"""
    task = AITask(task_type="video_analysis", status="pending", created_by=uuid.uuid4())
    transition(task, "processing", actor="worker")
    assert task.status == "processing"

    for source, target, actor in [
        ("completed", "processing", "worker"),
        ("failed", "pending", "worker"),
        ("cancelled", "processing", "worker"),
        ("pending", "completed", "worker"),
        ("processing", "pending", "worker"),  # 仅 reaper 可恢复
        ("processing", "pending", "user"),
    ]:
        bad = AITask(task_type="video_analysis", status=source, created_by=uuid.uuid4())
        with pytest.raises(AppException) as exc_info:
            transition(bad, target, actor=actor)
        assert exc_info.value.code == "TASK_STATE_CONFLICT"
        assert exc_info.value.status_code == 409

    # reaper 恢复路径合法
    stale = AITask(task_type="video_analysis", status="processing", created_by=uuid.uuid4())
    transition(stale, "pending", actor="reaper", reason="lease expired")
    assert stale.status == "pending"


# ---------- 2. 幂等提交 ----------


def test_idempotent_generate_returns_same_task(client):
    tokens = register(client)
    headers = {**auth_headers(tokens), "Idempotency-Key": "gen-key-1"}
    from .helpers import FAKE_MP4

    resp1 = client.post(
        "/api/inspection-record/generate",
        headers=headers,
        files={"video": ("scene.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp1.status_code == 200
    resp2 = client.post(
        "/api/inspection-record/generate",
        headers=headers,
        files={"video": ("scene.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp2.status_code == 200
    assert resp1.json()["task_id"] == resp2.json()["task_id"]
    wait_task(client, tokens, resp1.json()["task_id"])
    # 不产生重复业务草稿
    records = client.get("/api/inspection-record", headers=auth_headers(tokens)).json()
    assert records["total"] == 1


def test_idempotency_key_with_different_body_returns_409(client):
    tokens = register(client)
    headers = {**auth_headers(tokens), "Idempotency-Key": "gen-key-2"}
    from .helpers import FAKE_MP4

    resp1 = client.post(
        "/api/inspection-record/generate",
        headers=headers,
        files={"video": ("scene.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp1.status_code == 200
    wait_task(client, tokens, resp1.json()["task_id"])
    resp2 = client.post(
        "/api/inspection-record/generate",
        headers=headers,
        files={"video": ("scene.mp4", FAKE_MP4, "video/mp4")},
        data={"remarks": "不同的请求体"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_idempotent_knowledge_upload_returns_same_document(client):
    tokens = register(client, "admin@example.com")
    make_admin(tokens["user"]["id"])
    headers = {**auth_headers(tokens), "Idempotency-Key": "kb-key-1"}
    content = "消防法条文内容".encode("utf-8")

    resp1 = client.post(
        "/api/knowledge/documents",
        headers=headers,
        files={"file": ("fire.txt", content, "text/plain")},
    )
    assert resp1.status_code == 200, resp1.text
    resp2 = client.post(
        "/api/knowledge/documents",
        headers=headers,
        files={"file": ("fire.txt", content, "text/plain")},
    )
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()  # 幂等命中优先于 DOCUMENT_DUPLICATE
    wait_task(client, tokens, resp1.json()["task_id"])


def test_idempotent_rebuild_returns_same_task(client):
    tokens = register(client, "admin@example.com")
    make_admin(tokens["user"]["id"])
    headers = {**auth_headers(tokens), "Idempotency-Key": "rebuild-key-1"}
    resp1 = client.post("/api/knowledge/rebuild", headers=headers)
    assert resp1.status_code == 200
    wait_task(client, tokens, resp1.json()["task_id"])
    resp2 = client.post("/api/knowledge/rebuild", headers=headers)
    assert resp2.status_code == 200
    assert resp1.json()["task_id"] == resp2.json()["task_id"]


# ---------- 3. 重试上限与死信 ----------


def test_retry_exhaustion_dead_letters_with_retry_exhausted(client):
    """默认 max_attempts=3：第 3 次失败即 RETRY_EXHAUSTED，并记死信审计。"""
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    first = wait_task(client, tokens, task_id)
    assert first["error_code"] == "AI_SERVICE_NOT_CONFIGURED"

    # 第 2、3 次尝试
    second_id = client.post(
        f"/api/tasks/{task_id}/retry", headers=auth_headers(tokens)
    ).json()["task_id"]
    second = wait_task(client, tokens, second_id)
    assert second["error_code"] == "AI_SERVICE_NOT_CONFIGURED"  # 未达上限保持原码
    third_id = client.post(
        f"/api/tasks/{second_id}/retry", headers=auth_headers(tokens)
    ).json()["task_id"]
    third = wait_task(client, tokens, third_id)
    assert third["status"] == "failed"
    assert third["error_code"] == "RETRY_EXHAUSTED"
    assert "重试上限" in third["error_message"]

    with _db() as session:
        third_task = session.get(AITask, uuid.UUID(third_id))
        assert third_task.attempt_count == 3
        assert third_task.max_attempts == 3
        assert third_task.input_data["retry_of"] == second_id
        actions = [
            row.action
            for row in session.query(AuditLog)
            .filter(AuditLog.entity_type == "ai_task")
            .all()
        ]
        assert actions.count("task.retry") == 2
        assert "task.dead_letter" in actions


# ---------- 4. reaper 卡住任务恢复 ----------


def _make_stuck_task(user_id: str, *, attempt_count: int, max_attempts: int = 3) -> str:
    with _db() as session:
        task = AITask(
            task_type="inspection_record_generation",
            status="processing",
            attempt_count=attempt_count,
            max_attempts=max_attempts,
            worker_id="dead-worker",
            lease_expires_at=utc_now() - timedelta(seconds=10),
            input_data={},
            created_by=uuid.UUID(user_id),
        )
        session.add(task)
        session.commit()
        return str(task.id)


class _StubExecutor:
    def __init__(self):
        self.submitted: list[uuid.UUID] = []

    def submit(self, task_id: uuid.UUID) -> None:
        self.submitted.append(task_id)

    def request_cancel(self, task_id: uuid.UUID) -> None:  # pragma: no cover
        pass

    def shutdown(self) -> None:  # pragma: no cover
        pass


def test_reaper_requeues_stale_task_with_remaining_attempts(client):
    tokens = register(client)
    task_id = _make_stuck_task(tokens["user"]["id"], attempt_count=1)
    stub = _StubExecutor()
    with _db() as session:
        recovered = recover_stale_tasks(session, executor=stub)
    assert recovered == [uuid.UUID(task_id)]
    assert stub.submitted == [uuid.UUID(task_id)]
    with _db() as session:
        task = session.get(AITask, uuid.UUID(task_id))
        assert task.status == "pending"
        assert task.worker_id is None
        assert task.lease_expires_at is None
        assert task.error_code == "STALE_TASK_RECOVERED"


def test_reaper_dead_letters_stale_task_at_max_attempts(client):
    tokens = register(client)
    task_id = _make_stuck_task(tokens["user"]["id"], attempt_count=3)
    stub = _StubExecutor()
    with _db() as session:
        recover_stale_tasks(session, executor=stub)
    assert stub.submitted == []
    with _db() as session:
        task = session.get(AITask, uuid.UUID(task_id))
        assert task.status == "failed"
        assert task.error_code == "STALE_TASK_RECOVERED"
        assert task.completed_at is not None
        notification = (
            session.query(Notification)
            .filter(Notification.entity_id == task.id, Notification.type == "task_failed")
            .one()
        )
        assert notification.user_id == uuid.UUID(tokens["user"]["id"])
        assert (
            session.query(AuditLog)
            .filter(AuditLog.action == "task.dead_letter", AuditLog.entity_id == task.id)
            .count()
            == 1
        )


# ---------- 5. 通知 ----------


def test_terminal_task_creates_notification_and_endpoints(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    task_id = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id)  # failed（AI 未配置）

    resp = client.get("/api/notifications", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    item = body["items"][0]
    assert set(item.keys()) == {
        "id", "type", "title", "body", "entity_type", "entity_id", "read_at", "created_at",
    }
    assert item["type"] == "task_failed"
    assert item["entity_type"] == "inspection_record"  # entity 指向关联业务记录
    assert item["entity_id"] is not None
    assert item["read_at"] is None
    assert "失败" in item["title"]

    # 他人不可见、不可操作（404）
    assert client.get("/api/notifications", headers=auth_headers(other)).json()["total"] == 0
    resp = client.post(
        f"/api/notifications/{item['id']}/read", headers=auth_headers(other)
    )
    assert resp.status_code == 404

    # 标记已读（幂等）
    resp = client.post(
        f"/api/notifications/{item['id']}/read", headers=auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None
    body = client.get("/api/notifications", headers=auth_headers(tokens)).json()
    assert body["unread_count"] == 0
    body = client.get(
        "/api/notifications", params={"unread_only": True}, headers=auth_headers(tokens)
    ).json()
    assert body["total"] == 0

    # read-all
    task_id2 = generate_inspection(client, tokens)
    wait_task(client, tokens, task_id2)
    resp = client.post("/api/notifications/read-all", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
    body = client.get("/api/notifications", headers=auth_headers(tokens)).json()
    assert body["unread_count"] == 0


def test_cancel_writes_notification_and_audit(client):
    tokens = register(client)
    task_id = generate_inspection(client, tokens)
    resp = client.post(f"/api/tasks/{task_id}/cancel", headers=auth_headers(tokens))
    final = wait_task(client, tokens, task_id)
    if resp.status_code == 200:
        assert final["status"] == "cancelled"
        with _db() as session:
            assert (
                session.query(Notification)
                .filter(Notification.type == "task_cancelled")
                .count()
                == 1
            )
            assert (
                session.query(AuditLog)
                .filter(
                    AuditLog.action == "task.cancel",
                    AuditLog.entity_id == uuid.UUID(task_id),
                )
                .count()
                == 1
            )


# ---------- 6. 并发执行 ----------


def test_executor_runs_tasks_concurrently(monkeypatch):
    """EXECUTOR_WORKERS=2：两个任务并发执行互不干扰（时间窗重叠）。"""
    intervals: list[tuple[float, float]] = []
    lock = threading.Lock()

    def fake_run_task(task_id, cancel_event):
        start = time.monotonic()
        time.sleep(0.4)
        with lock:
            intervals.append((start, time.monotonic()))

    import app.services.tasks.worker as worker_module

    monkeypatch.setattr(worker_module, "run_task", fake_run_task)
    executor = InProcessTaskExecutor(max_workers=2)
    try:
        executor.submit(uuid.uuid4())
        executor.submit(uuid.uuid4())
    finally:
        executor.shutdown()
    assert len(intervals) == 2
    (s1, e1), (s2, e2) = intervals
    assert max(s1, s2) < min(e1, e2)  # 时间窗重叠 = 并发执行


def test_executor_workers_config_default():
    from app.core.config import get_settings

    assert get_settings().EXECUTOR_WORKERS == 2
