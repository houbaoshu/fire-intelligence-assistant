"""Statistics summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument
from app.models.photo_report import PhotoReport
from app.models.task import AITask
from app.models.user import User
from app.schemas.statistics import StatisticsResponse

logger = get_logger(__name__)

router = APIRouter(tags=["statistics"])


@router.get(
    "/",
    response_model=StatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get platform statistics summary",
)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatisticsResponse:
    """Return counts of key platform entities for the dashboard."""

    # Count inspection records (non-deleted)
    inspection_count = await db.scalar(
        select(func.count())
        .select_from(InspectionRecord)
        .where(InspectionRecord.deleted_at.is_(None))
    )

    # Count photo reports (non-deleted)
    photo_count = await db.scalar(
        select(func.count()).select_from(PhotoReport).where(PhotoReport.deleted_at.is_(None))
    )

    # Count interview records (non-deleted)
    interview_count = await db.scalar(
        select(func.count())
        .select_from(InterviewRecord)
        .where(InterviewRecord.deleted_at.is_(None))
    )

    # Count knowledge documents (non-deleted)
    knowledge_count = await db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(KnowledgeDocument.deleted_at.is_(None))
    )

    # Count active tasks (pending, queued, or processing)
    active_tasks_count = await db.scalar(
        select(func.count())
        .select_from(AITask)
        .where(AITask.status.in_(["pending", "queued", "processing"]))
    )

    # Count generated documents
    from app.models.document import GeneratedDocument

    generated_count = await db.scalar(select(func.count()).select_from(GeneratedDocument))

    return StatisticsResponse(
        inspection_records_count=inspection_count or 0,
        photo_reports_count=photo_count or 0,
        interview_records_count=interview_count or 0,
        knowledge_documents_count=knowledge_count or 0,
        active_tasks_count=active_tasks_count or 0,
        generated_documents_count=generated_count or 0,
    )
