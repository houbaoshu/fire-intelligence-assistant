"""Task endpoints (API.md §8)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import NotFoundError
from app.schemas.task import TaskActionResponse, TaskListResponse, TaskOut
from app.services.tasks.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_out(task) -> TaskOut:
    return TaskOut(
        task_id=str(task.id),
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        current_stage=task.current_stage,
        result_data=task.result_data,
        error_code=task.error_code,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _get_own_task(db, user, task_id: uuid.UUID):
    task = TaskService(db).get(task_id)
    if task.created_by != user.id and user.role not in ("admin", "supervisor"):
        raise NotFoundError("任务不存在")
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(user: CurrentUser, db: DB, task_id: uuid.UUID):
    return _task_out(_get_own_task(db, user, task_id))


@router.get("", response_model=TaskListResponse)
def list_tasks(
    user: CurrentUser,
    db: DB,
    limit: int = 20,
    status: str | None = None,
    task_type: str | None = None,
):
    if limit > 100:
        limit = 100
    items, total = TaskService(db).list(
        user.id, limit=limit, status=status, task_type=task_type
    )
    return TaskListResponse(items=[_task_out(t) for t in items], total=total)


@router.post("/{task_id}/retry", response_model=TaskActionResponse)
def retry_task(user: CurrentUser, db: DB, task_id: uuid.UUID):
    task = _get_own_task(db, user, task_id)
    new_task = TaskService(db).retry(task.id)
    db.commit()
    return TaskActionResponse(task_id=str(new_task.id), status="queued")


@router.post("/{task_id}/cancel", response_model=TaskActionResponse)
def cancel_task(user: CurrentUser, db: DB, task_id: uuid.UUID):
    task = _get_own_task(db, user, task_id)
    task = TaskService(db).cancel(task.id)
    db.commit()
    return TaskActionResponse(task_id=str(task.id), status=task.status)
