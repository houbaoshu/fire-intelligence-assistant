"""任务执行共享助手：worker 认领（租约）、续约、死信判定与结构化日志。

供 tasks/worker.py（业务管线任务）与 services/knowledge_indexing.py
（知识库任务）复用，保证两类执行体的追踪字段与日志信号一致
（specs/workflow.md §12）。
"""

import os
import socket
import threading
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.ai_task import AITask
from app.models.base import utc_now
from app.models.user import AuditLog
from app.repositories.user_repository import AuditLogRepository
from app.services.tasks.state_machine import transition

logger = get_logger("tasks.execution")

_PROCESS_ID = f"{socket.gethostname()}-{os.getpid()}"


def worker_identity() -> str:
    """worker 标识：主机-进程-线程（可观测性信号，无敏感内容）。"""
    return f"{_PROCESS_ID}-{threading.current_thread().name}"


def claim_task(session: Session, task: AITask, worker_id: str) -> None:
    """认领任务：pending → processing，写 worker_id 与租约，清理上轮错误。"""
    lease_seconds = get_settings().TASK_LEASE_SECONDS
    transition(task, "processing", actor="worker")
    now = utc_now()
    queued_at = task.queued_at or task.created_at
    if queued_at.tzinfo is None:
        # SQLite 驱动返回 naive datetime，统一按 UTC 解释
        from datetime import timezone

        queued_at = queued_at.replace(tzinfo=timezone.utc)
    queue_wait_ms = int((now - queued_at).total_seconds() * 1000)
    task.started_at = now
    task.worker_id = worker_id
    task.lease_expires_at = now + timedelta(seconds=lease_seconds)
    task.error_code = None
    task.error_message = None
    session.commit()
    logger.info(
        "task claimed: task_id=%s task_type=%s worker_id=%s attempt=%d/%d queue_wait_ms=%d",
        task.id,
        task.task_type,
        worker_id,
        task.attempt_count,
        task.max_attempts,
        queue_wait_ms,
    )


def renew_lease(task: AITask) -> None:
    """阶段推进时续约（调用方负责 commit）。"""
    task.lease_expires_at = utc_now() + timedelta(
        seconds=get_settings().TASK_LEASE_SECONDS
    )


def resolve_failure(task: AITask, code: str, message: str) -> tuple[str, str, bool]:
    """死信判定：达到重试上限的失败包装为 RETRY_EXHAUSTED。

    返回 (error_code, error_message, exhausted)。exhausted 时调用方应记死信审计。
    """
    if task.attempt_count >= task.max_attempts:
        return (
            "RETRY_EXHAUSTED",
            f"任务已尝试 {task.attempt_count} 次仍失败（{code}：{message}），"
            "已达重试上限，请检查输入或联系管理员",
            True,
        )
    return code, message, False


def audit_dead_letter(session: Session, task: AITask, original_code: str) -> None:
    """死信等价流程的审计记录（append-only，admin 可追踪）。"""
    AuditLogRepository(session).append(
        AuditLog(
            user_id=task.created_by,
            action="task.dead_letter",
            entity_type="ai_task",
            entity_id=task.id,
            details={
                "task_type": task.task_type,
                "attempt_count": task.attempt_count,
                "original_error_code": original_code,
            },
        )
    )


def log_terminal(
    task: AITask, *, error_code: str | None, stage_durations_ms: dict[str, int]
) -> None:
    """任务终态结构化日志：总时长、retry 次数、failure code、worker、终态。"""
    duration_ms = None
    if task.started_at is not None and task.completed_at is not None:
        duration_ms = int(
            (task.completed_at - task.started_at).total_seconds() * 1000
        )
    logger.info(
        "task terminal: task_id=%s task_type=%s status=%s error_code=%s "
        "attempt=%d/%d duration_ms=%s worker_id=%s stages=%s",
        task.id,
        task.task_type,
        task.status,
        error_code or "-",
        task.attempt_count,
        task.max_attempts,
        duration_ms if duration_ms is not None else "-",
        task.worker_id or "-",
        stage_durations_ms or "-",
    )
