from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import AppError
from app.core.permissions import authorized_user_ids
from app.db.models import AITask, User

logger = logging.getLogger("fire_intelligence.tasks")
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})
TaskHandler = Callable[["TaskContext"], dict[str, Any] | None]


@dataclass
class TaskContext:
    session: Session
    task: AITask
    application_state: Any

    def refresh(self) -> None:
        self.session.refresh(self.task)
        if self.task.cancel_requested:
            raise TaskCancelled

    def update(self, progress: int, stage: str) -> None:
        self.refresh()
        self.task.progress = max(self.task.progress, min(99, max(0, progress)))
        self.task.current_stage = stage
        self.task.updated_at = datetime.now(UTC)
        self.session.commit()


class TaskCancelled(Exception):
    pass


class TaskDispatcher:
    def __init__(
        self, factory: sessionmaker[Session], application_state: Any, workers: int
    ) -> None:
        self.factory = factory
        self.application_state = application_state
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fip-task")
        self.handlers: dict[str, TaskHandler] = {}
        self.active: set[uuid.UUID] = set()
        self.lock = Lock()

    def register(self, task_type: str, handler: TaskHandler) -> None:
        self.handlers[task_type] = handler

    def submit(self, task_id: uuid.UUID) -> None:
        with self.lock:
            if task_id in self.active:
                return
            self.active.add(task_id)
        self.executor.submit(self._execute, task_id)

    def recover_pending(self) -> int:
        with self.factory() as session:
            tasks = session.scalars(
                select(AITask).where(AITask.status.in_(("pending", "queued", "processing")))
            ).all()
            for task in tasks:
                task.status = "queued"
                task.current_stage = "recovered"
            session.commit()
            task_ids = [task.id for task in tasks]
        for task_id in task_ids:
            self.submit(task_id)
        return len(task_ids)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def _execute(self, task_id: uuid.UUID) -> None:
        try:
            with self.factory() as session:
                task = session.get(AITask, task_id)
                if task is None or task.status in TERMINAL_STATES:
                    return
                handler = self.handlers.get(task.task_type)
                if handler is None:
                    self._fail(
                        session, task, "TASK_TYPE_UNSUPPORTED", "No worker handles this task type."
                    )
                    return
                task.status = "processing"
                task.started_at = task.started_at or datetime.now(UTC)
                task.current_stage = task.current_stage or "starting"
                session.commit()
                context = TaskContext(
                    session=session, task=task, application_state=self.application_state
                )
                try:
                    result = handler(context) or {}
                    context.refresh()
                    existing = task.result_data or {}
                    task.result_data = {**existing, **result}
                    task.status = "completed"
                    task.progress = 100
                    task.current_stage = "completed"
                    task.completed_at = datetime.now(UTC)
                    task.error_code = None
                    task.error_message = None
                    session.commit()
                except TaskCancelled:
                    task.status = "cancelled"
                    task.current_stage = "cancelled"
                    task.completed_at = datetime.now(UTC)
                    session.commit()
                except AppError as error:
                    self._fail(session, task, error.code, error.message)
                except Exception:
                    logger.exception("task.failed", extra={"task_id": str(task_id)})
                    self._fail(
                        session,
                        task,
                        "TASK_EXECUTION_FAILED",
                        "The task could not be completed. Retry or contact an administrator.",
                    )
        finally:
            with self.lock:
                self.active.discard(task_id)

    @staticmethod
    def _fail(session: Session, task: AITask, code: str, message: str) -> None:
        result = task.result_data or {}
        entity_type = result.get("entity_type")
        entity_id = result.get("entity_id")
        if isinstance(entity_type, str) and isinstance(entity_id, str):
            from app.db.models import InspectionRecord, InterviewRecord, PhotoReport

            model = {
                "inspection_record": InspectionRecord,
                "photo_report": PhotoReport,
                "interview_record": InterviewRecord,
            }.get(entity_type)
            if model is not None:
                try:
                    entity: Any = session.get(model, uuid.UUID(entity_id))
                except ValueError:
                    entity = None
                if entity is not None and entity.status == "processing":
                    entity.status = "failed"
        task.status = "failed"
        task.current_stage = "failed"
        task.error_code = code
        task.error_message = message
        task.completed_at = datetime.now(UTC)
        session.commit()


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        task_type: str,
        user_id: uuid.UUID,
        input_data: dict[str, Any] | None = None,
        result_data: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> AITask:
        if idempotency_key:
            existing = self.session.scalar(
                select(AITask).where(
                    AITask.created_by == user_id,
                    AITask.task_type == task_type,
                    AITask.idempotency_key == idempotency_key,
                    AITask.status.not_in(TERMINAL_STATES),
                )
            )
            if existing:
                return existing
        task = AITask(
            task_type=task_type,
            status="queued",
            progress=0,
            current_stage="queued",
            input_data=input_data,
            result_data=result_data,
            idempotency_key=idempotency_key,
            created_by=user_id,
        )
        self.session.add(task)
        self.session.flush()
        return task

    def get_authorized(self, task_id: uuid.UUID, user: User) -> AITask:
        task = self.session.get(AITask, task_id)
        visible = authorized_user_ids(self.session, user)
        if task is None or (visible is not None and task.created_by not in visible):
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="Task not found.")
        return task
