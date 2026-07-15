"""Statistics service for dashboard."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.document import GeneratedDocument
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument
from app.models.photo_report import PhotoReport
from app.models.task import AITask
from app.models.user import User

logger = get_logger(__name__)


class StatisticsService:
    """Service for computing dashboard statistics."""

    async def get_statistics(
        self,
        user: User,
        db: AsyncSession,
    ) -> dict:
        """Get counts for dashboard statistics.

        Args:
            user: Current user.
            db: Database session.

        Returns:
            Dict with count fields.
        """
        logger.info("Statistics request", extra={"user_id": str(user.id)})

        # Count inspection records
        result = await db.execute(
            select(func.count(InspectionRecord.id)).where(
                InspectionRecord.created_by == str(user.id),
                InspectionRecord.deleted_at.is_(None),
            )
        )
        inspection_records_count = result.scalar() or 0

        # Count photo reports
        result = await db.execute(
            select(func.count(PhotoReport.id)).where(
                PhotoReport.created_by == str(user.id),
                PhotoReport.deleted_at.is_(None),
            )
        )
        photo_reports_count = result.scalar() or 0

        # Count interview records
        result = await db.execute(
            select(func.count(InterviewRecord.id)).where(
                InterviewRecord.created_by == str(user.id),
                InterviewRecord.deleted_at.is_(None),
            )
        )
        interview_records_count = result.scalar() or 0

        # Count knowledge documents
        result = await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.created_by == str(user.id),
                KnowledgeDocument.deleted_at.is_(None),
            )
        )
        knowledge_documents_count = result.scalar() or 0

        # Count active tasks
        result = await db.execute(
            select(func.count(AITask.id)).where(
                AITask.created_by == str(user.id),
                AITask.status.in_(["pending", "queued", "processing"]),
            )
        )
        active_tasks_count = result.scalar() or 0

        # Count generated documents
        result = await db.execute(
            select(func.count(GeneratedDocument.id)).where(
                GeneratedDocument.created_by == str(user.id)
            )
        )
        generated_documents_count = result.scalar() or 0

        return {
            "inspection_records_count": inspection_records_count,
            "photo_reports_count": photo_reports_count,
            "interview_records_count": interview_records_count,
            "knowledge_documents_count": knowledge_documents_count,
            "active_tasks_count": active_tasks_count,
            "generated_documents_count": generated_documents_count,
        }
