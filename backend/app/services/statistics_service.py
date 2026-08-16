"""Statistics service (API.md §7).

Counts come from existing business tables, follow soft-delete rules and are
scoped by the current user's role. Frontend never hard-codes metrics.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import AiTask
from app.models.document import GeneratedDocument
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument
from app.models.photo_report import PhotoReport


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db

    def _scope_for(self, user) -> str:
        return {
            "admin": "system",
            "supervisor": "organization",
            "inspector": "personal",
            "viewer": "personal",
        }.get(user.role, "personal")

    def _record_filter(self, model, user):
        if user.role == "admin":
            return model.deleted_at.is_(None)
        if user.role == "supervisor":
            # supervisor sees the whole organization (records whose creator
            # belongs to the same organization); unassigned supervisors see all
            if user.organization_id:
                from app.models.user import User

                return model.deleted_at.is_(None) & (
                    model.created_by.in_(
                        select(User.id).where(
                            User.organization_id == user.organization_id,
                            User.deleted_at.is_(None),
                        )
                    )
                )
            return model.deleted_at.is_(None)
        return model.deleted_at.is_(None) & (model.created_by == user.id)

    def _group_stats(self, model, user):
        filt = self._record_filter(model, user)
        total = int(self.db.scalar(select(func.count(model.id)).where(filt)) or 0)
        rows = (
            self.db.execute(
                select(model.status, func.count(model.id)).where(filt).group_by(model.status)
            ).all()
        )
        return {"total": total, "by_status": {s: int(c) for s, c in rows}}

    def get(self, user) -> dict:
        scope = self._scope_for(user)

        # tasks: own tasks for everyone (admin sees all)
        if user.role == "admin":
            task_filt = AiTask.id.is_not(None)
        else:
            task_filt = AiTask.created_by == user.id
        task_total = int(self.db.scalar(select(func.count(AiTask.id)).where(task_filt)) or 0)
        task_rows = (
            self.db.execute(
                select(AiTask.status, func.count(AiTask.id)).where(task_filt).group_by(AiTask.status)
            ).all()
        )
        task_stats = {"total": task_total, "by_status": {s: int(c) for s, c in task_rows}}

        knowledge_filt = KnowledgeDocument.deleted_at.is_(None)
        doc_total = int(self.db.scalar(select(func.count(KnowledgeDocument.id)).where(knowledge_filt)) or 0)
        indexed = int(
            self.db.scalar(
                select(func.count(KnowledgeDocument.id)).where(
                    knowledge_filt, KnowledgeDocument.status == "indexed"
                )
            )
            or 0
        )
        indexing = int(
            self.db.scalar(
                select(func.count(KnowledgeDocument.id)).where(
                    knowledge_filt, KnowledgeDocument.status.in_(["parsing", "indexing"])
                )
            )
            or 0
        )
        failed = int(
            self.db.scalar(
                select(func.count(KnowledgeDocument.id)).where(
                    knowledge_filt, KnowledgeDocument.status == "failed"
                )
            )
            or 0
        )
        last_indexed = self.db.scalar(
            select(KnowledgeDocument.updated_at)
            .where(knowledge_filt, KnowledgeDocument.status == "indexed")
            .order_by(KnowledgeDocument.updated_at.desc())
            .limit(1)
        )

        gen_total = int(
            self.db.scalar(select(func.count(GeneratedDocument.id))) or 0
        )

        return {
            "scope": scope,
            "generated_at": _utcnow(),
            "records": {
                "inspection_records": self._group_stats(InspectionRecord, user),
                "photo_reports": self._group_stats(PhotoReport, user),
                "interview_records": self._group_stats(InterviewRecord, user),
            },
            "tasks": task_stats,
            "knowledge": {
                "document_count": doc_total,
                "indexed_count": indexed,
                "indexing_count": indexing,
                "failed_count": failed,
                "last_indexed_at": last_indexed,
            },
            "generated_documents": {"total": gen_total},
        }
