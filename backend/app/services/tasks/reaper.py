"""卡住任务（stuck task）检测与恢复：reaper（specs/workflow.md §11/§12）。

worker 崩溃后任务停留在 processing 且租约过期。reaper 在应用启动时执行一次，
并以后台守护线程周期扫描（挂 lifespan，见 app/main.py）：

- ``attempt_count < max_attempts``：重置为 pending 并重新入队（不清空进度，
  重新认领时清理错误字段）；error 标记为 STALE_TASK_RECOVERED 供排查。
- 达到上限：落 failed 终态（STALE_TASK_RECOVERED，可读错误信息），
  记死信审计并通知创建者。

重复定稿防护：重新入队的任务仍走既有 finalized 防覆盖守卫
（worker._apply_result / TaskService._guard_finalized_record），
worker 重启不会静默重复定稿。
"""

import threading
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db import SessionLocal
from app.models.ai_task import AITask
from app.models.base import utc_now
from app.models.user import AuditLog
from app.repositories.user_repository import AuditLogRepository
from app.services.notification_service import notify_task_terminal
from app.services.tasks.executor import TaskExecutor
from app.services.tasks.state_machine import transition

logger = get_logger("tasks.reaper")


def recover_stale_tasks(
    session: Session,
    *,
    executor: TaskExecutor | None = None,
    now: datetime | None = None,
) -> list[uuid.UUID]:
    """恢复租约过期且仍在 processing 的任务，返回被恢复的任务 id 列表。

    ``executor`` 为 None 时仅重置状态不重新入队（测试用）；
    生产路径由 reaper 线程传入进程级执行器。
    """
    now = now or utc_now()
    stmt = select(AITask).where(
        AITask.status == "processing",
        AITask.lease_expires_at.is_not(None),
        AITask.lease_expires_at < now,
    )
    stale = list(session.execute(stmt).scalars().all())
    recovered: list[uuid.UUID] = []
    for task in stale:
        if task.attempt_count < task.max_attempts:
            # 恢复为可重试状态：重新入队（同一 attempt 的 reclaim，不递增计数）
            transition(task, "pending", actor="reaper", reason="lease expired")
            task.queued_at = now
            task.started_at = None
            task.worker_id = None
            task.lease_expires_at = None
            task.current_stage = None
            task.error_code = "STALE_TASK_RECOVERED"
            task.error_message = "任务执行中断（worker 租约过期），已自动重新入队"
            session.commit()
            logger.warning(
                "stale task requeued: task_id=%s task_type=%s attempt=%d/%d worker_id=%s",
                task.id, task.task_type, task.attempt_count, task.max_attempts, "-",
            )
            if executor is not None:
                executor.submit(task.id)
        else:
            transition(task, "failed", actor="reaper", reason="lease expired")
            task.error_code = "STALE_TASK_RECOVERED"
            task.error_message = (
                "任务多次执行中断且已达重试上限，已标记失败，请检查输入后重新提交"
            )
            task.completed_at = now
            task.lease_expires_at = None
            AuditLogRepository(session).append(
                AuditLog(
                    user_id=task.created_by,
                    action="task.dead_letter",
                    entity_type="ai_task",
                    entity_id=task.id,
                    details={
                        "task_type": task.task_type,
                        "attempt_count": task.attempt_count,
                        "original_error_code": "STALE_TASK_RECOVERED",
                    },
                )
            )
            notify_task_terminal(session, task)
            session.commit()
            logger.warning(
                "stale task dead-lettered: task_id=%s task_type=%s attempt=%d/%d",
                task.id, task.task_type, task.attempt_count, task.max_attempts,
            )
        recovered.append(task.id)
    return recovered


class TaskReaper:
    """周期扫描卡住任务的守护线程（挂 FastAPI lifespan）。"""

    def __init__(self, executor: TaskExecutor, interval_seconds: float) -> None:
        self._executor = executor
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._run_once()  # 启动时先恢复一次（覆盖上次进程崩溃残留）
        self._thread = threading.Thread(
            target=self._loop, name="task-reaper", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            self._run_once()

    def _run_once(self) -> None:
        session = SessionLocal()
        try:
            recovered = recover_stale_tasks(session, executor=self._executor)
            if recovered:
                logger.info("reaper recovered %d stale task(s)", len(recovered))
        except Exception:
            logger.error("reaper 扫描失败", exc_info=True)
        finally:
            session.close()


def create_reaper(executor: TaskExecutor) -> TaskReaper:
    return TaskReaper(executor, get_settings().TASK_REAPER_INTERVAL_SECONDS)
