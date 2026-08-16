"""Task handler registry.

Business modules register handlers for their task types; the worker resolves
handlers by task_type. Keeps the queue provider decoupled from business logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session


@dataclass
class TaskContext:
    task_id: uuid.UUID
    task_type: str
    user_id: uuid.UUID
    input_data: dict[str, Any]
    db: Session
    attempt: int = 1
    _progress: int = 0

    def set_progress(self, progress: int, stage: str | None = None) -> None:
        from app.services.tasks.task_service import TaskService

        if not (0 <= progress <= 100):
            raise ValueError("progress must be 0..100")
        TaskService(self.db).update_progress(
            self.task_id, progress=progress, stage=stage
        )
        self.db.commit()

    def set_result(self, result: dict[str, Any]) -> None:
        from app.services.tasks.task_service import TaskService

        TaskService(self.db).store_result(self.task_id, result)
        self.db.commit()

    def fail(self, error_code: str, error_message: str) -> None:
        from app.services.tasks.task_service import TaskService

        TaskService(self.db).mark_failed(self.task_id, error_code, error_message)
        self.db.commit()


Handler = Callable[[TaskContext], None]

_REGISTRY: dict[str, Handler] = {}


def register_handler(task_type: str) -> Callable[[Handler], Handler]:
    def decorator(fn: Handler) -> Handler:
        if task_type in _REGISTRY:
            raise RuntimeError(f"duplicate task handler: {task_type}")
        _REGISTRY[task_type] = fn
        return fn

    return decorator


def get_handler(task_type: str) -> Handler | None:
    return _REGISTRY.get(task_type)


def registered_types() -> list[str]:
    return sorted(_REGISTRY)
