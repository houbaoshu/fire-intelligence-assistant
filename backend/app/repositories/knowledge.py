"""Repository for KnowledgeDocument and KnowledgeIndexJob operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument, KnowledgeIndexJob


class KnowledgeRepository:
    """Encapsulates all database access for knowledge-base models."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── KnowledgeDocument ─────────────────────────────────────────────────

    async def get_by_id(self, doc_id: str) -> KnowledgeDocument | None:
        """Return a single knowledge document by id, excluding soft-deleted."""
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(self, skip: int = 0, limit: int = 100) -> list[KnowledgeDocument]:
        """Return a paginated list of non-deleted knowledge documents."""
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.deleted_at.is_(None))
            .order_by(KnowledgeDocument.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> KnowledgeDocument:
        """Create a new knowledge document from keyword arguments."""
        doc = KnowledgeDocument(**kwargs)
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def update(self, doc_id: str, **kwargs) -> KnowledgeDocument:
        """Update an existing knowledge document and return the refreshed instance.

        Raises ``ValueError`` if the document does not exist.
        """
        doc = await self.get_by_id(doc_id)
        if doc is None:
            raise ValueError(f"KnowledgeDocument {doc_id!r} not found")
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def soft_delete(self, doc_id: str) -> None:
        """Mark a knowledge document as deleted by setting ``deleted_at``."""
        doc = await self.get_by_id(doc_id)
        if doc is None:
            raise ValueError(f"KnowledgeDocument {doc_id!r} not found")
        doc.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def count_all(self) -> int:
        """Return the total count of non-deleted knowledge documents."""
        stmt = (
            select(func.count())
            .select_from(KnowledgeDocument)
            .where(KnowledgeDocument.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── KnowledgeIndexJob ─────────────────────────────────────────────────

    async def create_index_job(self, **kwargs) -> KnowledgeIndexJob:
        """Create a new knowledge index job from keyword arguments."""
        job = KnowledgeIndexJob(**kwargs)
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def update_index_job(self, job_id: str, **kwargs) -> KnowledgeIndexJob:
        """Update an existing index job and return the refreshed instance.

        Raises ``ValueError`` if the job does not exist.
        """
        stmt = select(KnowledgeIndexJob).where(KnowledgeIndexJob.id == job_id)
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            raise ValueError(f"KnowledgeIndexJob {job_id!r} not found")
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await self.db.flush()
        await self.db.refresh(job)
        return job
