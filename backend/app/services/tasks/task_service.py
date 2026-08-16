"""Task service: create / query / progress / retry / cancel.

State machine (single source of truth):
    pending -> queued -> processing -> completed | failed | cancelled
    retry:   failed | cancelled -> (new task instance)
    cancel:  pending | queued | processing -> cancelled
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, TaskStateConflictError
from app.models.enums import TASK_STATUSES, TASK_TYPES
from app.models.task import AiTask


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Allowed transitions; values are statuses reachable from the key.
TRANSITIONS: dict[str, set[str]] = {
    "pending": {"queued", "processing", "completed", "failed", "cancelled"},
    "queued": {"processing", "cancelled", "failed"},
    "processing": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": {"queued", "cancelled"},  # manual retry re-queues the SAME record in v1
    "cancelled": set(),
}

CANCELABLE = {"pending", "queued", "processing"}
RETRYABLE = {"failed", "cancelled"}
TERMINAL = {"completed", "failed", "cancelled"}


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    # ---- creation -----------------------------------------------------------

    def create_task(
        self,
        task_type: str,
        user_id: uuid.UUID,
        *,
        input_data: dict | None = None,
        parent_task_id: uuid.UUID | None = None,
        enqueue: bool = True,
        idempotency_key: str | None = None,
    ) -> AiTask:
        if task_type not in TASK_TYPES:
            raise ValueError(f"未知任务类型: {task_type}")
        # idempotency: return the existing task instead of creating a duplicate
        if idempotency_key:
            existing = self.db.scalar(
                select(AiTask).where(
                    AiTask.created_by == user_id,
                    AiTask.task_type == task_type,
                    AiTask.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                return existing
        task = AiTask(
            task_type=task_type,
            status="queued" if enqueue else "pending",
            progress=0,
            input_data=input_data or {},
            created_by=user_id,
            parent_task_id=parent_task_id,
            idempotency_key=idempotency_key,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def _get(self, task_id: uuid.UUID | str) -> AiTask:
        task = self.db.get(AiTask, uuid.UUID(str(task_id)))
        if task is None:
            raise NotFoundError("任务不存在")
        return task

    # ---- state changes ------------------------------------------------------

    def _transition(self, task: AiTask, to: str) -> None:
        allowed = TRANSITIONS.get(task.status, set())
        if to not in allowed:
            raise TaskStateConflictError(
                f"任务当前状态为 {task.status},不能执行该操作"
            )
        task.status = to

    def update_progress(self, task_id: uuid.UUID | str, progress: int, stage: str | None = None) -> AiTask:
        task = self._get(task_id)
        if task.status != "processing":
            # allow progress updates while processing only
            if task.status in ("queued", "pending"):
                pass
            else:
                return task
        task.progress = max(0, min(100, progress))
        if stage is not None:
            task.current_stage = stage
        task.updated_at = _utcnow()
        return task

    def store_result(self, task_id: uuid.UUID | str, result: dict) -> AiTask:
        task = self._get(task_id)
        task.result_data = result
        return task

    def mark_completed(self, task_id: uuid.UUID | str, result: dict | None = None) -> AiTask:
        task = self._get(task_id)
        self._transition(task, "completed")
        task.progress = 100
        if result is not None:
            task.result_data = result
        task.completed_at = _utcnow()
        return task

    def mark_failed(self, task_id: uuid.UUID | str, error_code: str, error_message: str) -> AiTask:
        task = self._get(task_id)
        if task.status not in ("pending", "queued", "processing"):
            return task
        task.status = "failed"
        task.error_code = error_code
        task.error_message = error_message
        task.completed_at = _utcnow()
        return task

    def claim_next(self) -> AiTask | None:
        """Claim the oldest queued task (single-writer friendly)."""
        stmt = (
            select(AiTask)
            .where(AiTask.status == "queued")
            .order_by(AiTask.created_at.asc())
            .limit(1)
        )
        task = self.db.scalar(stmt)
        if task is None:
            return None
        task.status = "processing"
        task.started_at = _utcnow()
        task.attempt += 1
        self.db.commit()
        self.db.refresh(task)
        return task

    # ---- queries ------------------------------------------------------------

    def get(self, task_id: uuid.UUID | str) -> AiTask:
        return self._get(task_id)

    def list(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
        status: str | None = None,
        task_type: str | None = None,
    ) -> tuple[list[AiTask], int]:
        from sqlalchemy import func

        base = select(AiTask).where(AiTask.created_by == user_id)
        total = int(
            self.db.scalar(
                select(func.count(AiTask.id)).where(AiTask.created_by == user_id)
            )
            or 0
        )
        stmt = base
        if status:
            stmt = stmt.where(AiTask.status == status)
        if task_type:
            stmt = stmt.where(AiTask.task_type == task_type)
        items = list(
            self.db.scalars(
                stmt.order_by(AiTask.created_at.desc()).limit(limit)
            ).all()
        )
        return items, total

    def retry(self, task_id: uuid.UUID | str) -> AiTask:
        """Create a NEW task instance for a failed/cancelled task.

        The original task is preserved for audit; the new task carries a
        parent_task_id reference and is re-queued. Retry depth is bounded by
        TASK_MAX_RETRIES (walking the parent chain).
        """
        from app.core.config import get_settings

        task = self._get(task_id)
        if task.status not in RETRYABLE:
            raise TaskStateConflictError("仅失败或已取消的任务可以重试")
        max_retries = get_settings().TASK_MAX_RETRIES
        depth = 0
        current: AiTask | None = task
        while current is not None:
            depth += 1
            if depth > max_retries:
                raise TaskStateConflictError(
                    f"重试次数已达上限({max_retries}),请创建新的生成任务"
                )
            current = self.db.get(AiTask, current.parent_task_id) if current.parent_task_id else None
        new_task = AiTask(
            task_type=task.task_type,
            status="queued",
            progress=0,
            input_data=task.input_data,
            result_data=None,
            created_by=task.created_by,
            parent_task_id=task.id,
            idempotency_key=None,  # new attempt is a distinct task instance
        )
        self.db.add(new_task)
        self.db.flush()
        return new_task

    def cancel(self, task_id: uuid.UUID | str) -> AiTask:
        task = self._get(task_id)
        if task.status not in CANCELABLE:
            raise TaskStateConflictError("仅待处理、排队或处理中的任务可以取消")
        task.status = "cancelled"
        task.completed_at = _utcnow()
        return task

    def count_by_status(self, user_id: uuid.UUID) -> dict[str, int]:
        from sqlalchemy import func

        rows = (
            self.db.execute(
                select(AiTask.status, func.count(AiTask.id))
                .where(AiTask.created_by == user_id)
                .group_by(AiTask.status)
            ).all()
        )
        return {status: int(count) for status, count in rows}

    def count_all_by_status(self) -> dict[str, int]:
        from sqlalchemy import func

        rows = self.db.execute(select(AiTask.status, func.count(AiTask.id)).group_by(AiTask.status)).all()
        return {status: int(count) for status, count in rows}

    def total_count(self) -> int:
        from sqlalchemy import func

        return int(self.db.scalar(select(func.count(AiTask.id))) or 0)
