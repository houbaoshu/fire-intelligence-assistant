"""Repository for AITask database operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import AITask


class TaskRepository:
    """Encapsulates all database access for :class:`AITask`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(self, task_id: str) -> AITask | None:
        """Return a single AI task by id, or *None* if not found."""
        stmt = select(AITask).where(AITask.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    async def create(self, **kwargs) -> AITask:
        """Create a new AI task from keyword arguments."""
        task = AITask(**kwargs)
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    # ── Update helpers ────────────────────────────────────────────────────

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress: int | None = None,
        current_stage: str | None = None,
        result_data: dict | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AITask:
        """Update the status (and optional progress fields) of an AI task.

        Raises ``ValueError`` if the task does not exist.
        """
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"AITask {task_id!r} not found")

        task.status = status
        if progress is not None:
            task.progress = progress
        if current_stage is not None:
            task.current_stage = current_stage
        if result_data is not None:
            task.result_data = result_data
        if error_code is not None:
            task.error_code = error_code
        if error_message is not None:
            task.error_message = error_message

        task.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def mark_started(self, task_id: str) -> None:
        """Transition a task to *processing* and record the start time."""
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"AITask {task_id!r} not found")
        task.status = "processing"
        task.started_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.db.flush()

    async def mark_completed(self, task_id: str, result_data: dict | None = None) -> None:
        """Transition a task to *completed* and optionally store results."""
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"AITask {task_id!r} not found")
        task.status = "completed"
        task.progress = 100
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        if result_data is not None:
            task.result_data = result_data
        await self.db.flush()

    async def mark_failed(self, task_id: str, error_code: str, error_message: str) -> None:
        """Transition a task to *failed* with error details."""
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"AITask {task_id!r} not found")
        task.status = "failed"
        task.error_code = error_code
        task.error_message = error_message
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self.db.flush()

    # ── Count ─────────────────────────────────────────────────────────────

    async def count_active_by_user(self, user_id: str) -> int:
        """Count tasks for a user that are not yet in a terminal state.

        Active states: ``pending``, ``queued``, ``processing``.
        """
        stmt = (
            select(func.count())
            .select_from(AITask)
            .where(
                AITask.created_by == user_id,
                AITask.status.in_(["pending", "queued", "processing"]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()
