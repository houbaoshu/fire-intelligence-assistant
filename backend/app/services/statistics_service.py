"""Statistics 聚合（API.md §7）。

所有计数来自既有业务表并遵循软删除规则；by_status 只含有数据的键。
scope 按角色：admin=system；其余 personal（supervisor 组织范围属 M6，见
DATABASE.md「数据归属」，落地后在此处扩展）。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_task import AITask
from app.models.generated_document import GeneratedDocument
from app.models.inspection import InspectionRecord
from app.models.interview import InterviewRecord
from app.models.knowledge import KnowledgeDocument
from app.models.photo_report import PhotoReport
from app.models.user import User
from app.repositories.knowledge_repository import aggregate_status_counts
from app.schemas.statistics import (
    GeneratedDocumentsStats,
    KnowledgeStats,
    RecordsStats,
    StatisticsResponse,
    StatusCount,
)


class StatisticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user: User) -> StatisticsResponse:
        is_admin = user.role == "admin"
        scope = "system" if is_admin else "personal"
        owner = None if is_admin else user.id
        return StatisticsResponse(
            scope=scope,
            generated_at=datetime.now(timezone.utc),
            records=RecordsStats(
                inspection_records=self._record_stats(InspectionRecord, owner),
                photo_reports=self._record_stats(PhotoReport, owner),
                interview_records=self._record_stats(InterviewRecord, owner),
            ),
            tasks=self._task_stats(owner),
            # 知识库为全库共享资源，计数不按个人归属过滤
            knowledge=KnowledgeStats(**aggregate_status_counts(self._knowledge_counts())),
            generated_documents=GeneratedDocumentsStats(
                total=self._generated_documents_total(owner)
            ),
        )

    def _record_stats(self, model, owner: uuid.UUID | None) -> StatusCount:
        stmt = select(model.status, func.count()).where(model.deleted_at.is_(None))
        if owner is not None:
            stmt = stmt.where(model.created_by == owner)
        stmt = stmt.group_by(model.status)
        by_status = {status: count for status, count in self.session.execute(stmt).all()}
        return StatusCount(total=sum(by_status.values()), by_status=by_status)

    def _task_stats(self, owner: uuid.UUID | None) -> StatusCount:
        stmt = select(AITask.status, func.count())
        if owner is not None:
            stmt = stmt.where(AITask.created_by == owner)
        stmt = stmt.group_by(AITask.status)
        by_status = {status: count for status, count in self.session.execute(stmt).all()}
        return StatusCount(total=sum(by_status.values()), by_status=by_status)

    def _knowledge_counts(self) -> dict[str, int]:
        stmt = (
            select(KnowledgeDocument.status, func.count())
            .where(KnowledgeDocument.deleted_at.is_(None))
            .group_by(KnowledgeDocument.status)
        )
        return {status: count for status, count in self.session.execute(stmt).all()}

    def _generated_documents_total(self, owner: uuid.UUID | None) -> int:
        stmt = select(func.count()).select_from(GeneratedDocument)
        if owner is not None:
            stmt = stmt.where(GeneratedDocument.created_by == owner)
        return self.session.execute(stmt).scalar_one()
