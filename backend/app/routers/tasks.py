"""Async task status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.task import AITask
from app.models.user import User
from app.schemas.task import TaskResponse

logger = get_logger(__name__)

router = APIRouter(tags=["tasks"])


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task status and progress",
)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Return the current status, progress, and result of an async task."""
    result = await db.execute(select(AITask).where(AITask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise NotFoundException(f"Task '{task_id}' not found")

    return TaskResponse.model_validate(task)
