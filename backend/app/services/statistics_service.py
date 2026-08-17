"""Statistics 聚合（API.md §7）。

所有计数来自既有业务表并遵循软删除规则；by_status 只含有数据的键。
scope 按角色（DATABASE.md「数据归属」）：admin=system；supervisor=organization
（按记录创建者所属组织过滤；未分配组织的 supervisor 查看全部，scope 记为
system）；inspector/viewer=personal。
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
from app.repositories.user_repository import UserRepository
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

    def _scope(self, user: User) -> tuple[str, list[uuid.UUID] | None]:
        """返回 (scope, creator_ids)：creator_ids 为 None 表示不按创建者过滤。"""
        if user.role == "admin":
            return "system", None
        if user.role == "supervisor":
            if user.organization_id is not None:
                ids = UserRepository(self.session).ids_in_organization(
                    user.organization_id
                )
                return "organization", ids
            # 未分配组织的 supervisor 默认查看全部
            return "system", None
        return "personal", [user.id]

    def get(self, user: User) -> StatisticsResponse:
        scope, creator_ids = self._scope(user)
        return StatisticsResponse(
            scope=scope,
            generated_at=datetime.now(timezone.utc),
            records=RecordsStats(
                inspection_records=self._record_stats(InspectionRecord, creator_ids),
                photo_reports=self._record_stats(PhotoReport, creator_ids),
                interview_records=self._record_stats(InterviewRecord, creator_ids),
            ),
            tasks=self._task_stats(creator_ids),
            # 知识库为全库共享资源，计数不按个人归属过滤
            knowledge=KnowledgeStats(**aggregate_status_counts(self._knowledge_counts())),
            generated_documents=GeneratedDocumentsStats(
                total=self._generated_documents_total(creator_ids)
            ),
        )

    def _record_stats(self, model, creator_ids: list[uuid.UUID] | None) -> StatusCount:
        stmt = select(model.status, func.count()).where(model.deleted_at.is_(None))
        if creator_ids is not None:
            stmt = stmt.where(model.created_by.in_(creator_ids))
        stmt = stmt.group_by(model.status)
        by_status = {status: count for status, count in self.session.execute(stmt).all()}
        return StatusCount(total=sum(by_status.values()), by_status=by_status)

    def _task_stats(self, creator_ids: list[uuid.UUID] | None) -> StatusCount:
        stmt = select(AITask.status, func.count())
        if creator_ids is not None:
            stmt = stmt.where(AITask.created_by.in_(creator_ids))
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

    def _generated_documents_total(self, creator_ids: list[uuid.UUID] | None) -> int:
        stmt = select(func.count()).select_from(GeneratedDocument)
        if creator_ids is not None:
            stmt = stmt.where(GeneratedDocument.created_by.in_(creator_ids))
        return self.session.execute(stmt).scalar_one()
