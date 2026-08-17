"""异步任务路由（API.md §8）。保持薄：解析请求、调用 TaskService。"""

import uuid

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import CurrentUser, DbSession, get_request_id, require_permission
from app.core.exceptions import AppException
from app.models.ai_task import TASK_STATUSES
from app.models.user import User
from app.schemas.tasks import (
    TaskCancelResponse,
    TaskListResponse,
    TaskResponse,
    TaskRetryResponse,
)
from app.services.tasks import get_task_executor
from app.services.tasks.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_response(task) -> TaskResponse:
    return TaskResponse(
        task_id=task.id,
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


@router.get("", response_model=TaskListResponse)
def list_tasks(
    session: DbSession,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> TaskListResponse:
    if status is not None and status not in TASK_STATUSES:
        raise AppException("VALIDATION_ERROR", f"非法任务状态: {status}", 400)
    tasks, total = TaskService(session, get_task_executor()).list(
        current_user, status, limit
    )
    return TaskListResponse(items=[_to_response(t) for t in tasks], total=total)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, session: DbSession, current_user: CurrentUser) -> TaskResponse:
    task = TaskService(session, get_task_executor()).get(task_id, current_user)
    return _to_response(task)


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
def retry_task(
    task_id: uuid.UUID,
    session: DbSession,
    request: Request,
    current_user: User = Depends(require_permission("task.manage")),
) -> TaskRetryResponse:
    new_task = TaskService(session, get_task_executor()).retry(
        task_id, current_user, request_id=get_request_id(request)
    )
    return TaskRetryResponse(task_id=new_task.id)


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(
    task_id: uuid.UUID,
    session: DbSession,
    request: Request,
    current_user: User = Depends(require_permission("task.manage")),
) -> TaskCancelResponse:
    task = TaskService(session, get_task_executor()).cancel(
        task_id, current_user, request_id=get_request_id(request)
    )
    return TaskCancelResponse(task_id=task.id, status=task.status)
