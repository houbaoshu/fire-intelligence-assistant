"""knowledge_documents / knowledge_index_jobs 数据访问。业务规则在 service 层。"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import INDEXING_STATUSES, KnowledgeDocument, KnowledgeIndexJob


class KnowledgeDocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, document_id: uuid.UUID) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self.session.add(document)
        self.session.flush()
        return document

    def find_by_checksum(self, checksum: str) -> KnowledgeDocument | None:
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.checksum == checksum,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.created_at)
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list(
        self, status: str | None, page: int, page_size: int
    ) -> tuple[list[KnowledgeDocument], int]:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(KnowledgeDocument.status == status)
        total = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.session.execute(
                stmt.order_by(KnowledgeDocument.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    def count_by_status(self) -> dict[str, int]:
        stmt = (
            select(KnowledgeDocument.status, func.count())
            .where(KnowledgeDocument.deleted_at.is_(None))
            .group_by(KnowledgeDocument.status)
        )
        return {status: count for status, count in self.session.execute(stmt).all()}

    def last_indexed_at(self) -> datetime | None:
        stmt = select(func.max(KnowledgeDocument.updated_at)).where(
            KnowledgeDocument.deleted_at.is_(None),
            KnowledgeDocument.status == "indexed",
        )
        return self.session.execute(stmt).scalar_one()


class KnowledgeIndexJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: KnowledgeIndexJob) -> KnowledgeIndexJob:
        self.session.add(job)
        self.session.flush()
        return job

    def get_by_task(self, ai_task_id: uuid.UUID) -> KnowledgeIndexJob | None:
        stmt = (
            select(KnowledgeIndexJob)
            .where(KnowledgeIndexJob.ai_task_id == ai_task_id)
            .order_by(KnowledgeIndexJob.created_at)
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()


def aggregate_status_counts(counts: dict[str, int]) -> dict[str, int]:
    """API.md §6 status 端点聚合：indexing_count 合并进行中的三个状态。"""
    return {
        "document_count": sum(counts.values()),
        "indexed_count": counts.get("indexed", 0),
        "indexing_count": sum(counts.get(s, 0) for s in INDEXING_STATUSES),
        "failed_count": counts.get("failed", 0),
    }
