from __future__ import annotations

import uuid
from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.dependencies import get_current_user
from app.core.exceptions import AppError
from app.core.permissions import authorized_user_ids
from app.db.models import AITask, User
from app.db.session import get_db
from app.schemas.business import TaskListResponse, TaskResponse
from app.services.audit import add_audit_log
from app.services.tasks import TERMINAL_STATES, TaskDispatcher, TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_response(task: AITask) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        current_stage=task.current_stage,
        message=task.error_message if task.status == "failed" else task.current_stage,
        result=task.result_data,
        error_code=task.error_code,
        error_message=task.error_message,
        attempt=task.attempt,
        cancel_requested=task.cancel_requested,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: str | None = None,
    task_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskListResponse:
    conditions: list[ColumnElement[bool]] = []
    visible = authorized_user_ids(session, user)
    if visible is not None:
        conditions.append(AITask.created_by.in_(visible))
    if status:
        conditions.append(AITask.status == status)
    if task_type:
        conditions.append(AITask.task_type == task_type)
    total = session.scalar(select(func.count(AITask.id)).where(*conditions)) or 0
    items = session.scalars(
        select(AITask)
        .where(*conditions)
        .order_by(AITask.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return TaskListResponse(items=[task_response(item) for item in items], total=total)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    return task_response(TaskService(session).get_authorized(task_id, user))


@router.post("/{task_id}/cancel", response_model=TaskResponse)
def cancel_task(
    task_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = TaskService(session).get_authorized(task_id, user)
    if task.status in TERMINAL_STATES:
        raise AppError(
            status_code=409, code="TASK_TERMINAL", message="The task has already finished."
        )
    task.cancel_requested = True
    add_audit_log(
        session,
        user_id=user.id,
        action="task.cancel",
        entity_type="ai_task",
        entity_id=task.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    return task_response(task)


@router.post("/{task_id}/retry", response_model=TaskResponse)
def retry_task(
    task_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    task = TaskService(session).get_authorized(task_id, user)
    if task.status not in {"failed", "cancelled"}:
        raise AppError(
            status_code=409,
            code="TASK_NOT_RETRYABLE",
            message="Only failed or cancelled tasks can be retried.",
        )
    if task.attempt >= request.app.state.settings.task_max_attempts:
        raise AppError(
            status_code=409,
            code="TASK_RETRY_EXHAUSTED",
            message="The task has reached the configured retry limit.",
        )
    task.status = "queued"
    task.progress = 0
    task.current_stage = "retry_queued"
    task.error_code = None
    task.error_message = None
    task.completed_at = None
    task.cancel_requested = False
    task.attempt += 1
    add_audit_log(
        session,
        user_id=user.id,
        action="task.retry",
        entity_type="ai_task",
        entity_id=task.id,
        request_id=getattr(request.state, "request_id", None),
        details={"attempt": task.attempt},
    )
    session.commit()
    dispatcher = cast(TaskDispatcher, request.app.state.task_dispatcher)
    dispatcher.submit(task.id)
    return task_response(task)
