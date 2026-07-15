"""Repository for InterviewRecord database operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewRecord


class InterviewRecordRepository:
    """Encapsulates all database access for :class:`InterviewRecord`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(self, record_id: str) -> InterviewRecord | None:
        """Return a single interview record by id, excluding soft-deleted."""
        stmt = select(InterviewRecord).where(
            InterviewRecord.id == record_id,
            InterviewRecord.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create / Update ───────────────────────────────────────────────────

    async def create(self, **kwargs) -> InterviewRecord:
        """Create a new interview record from keyword arguments."""
        record = InterviewRecord(**kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record_id: str, **kwargs) -> InterviewRecord:
        """Update an existing interview record and return the refreshed instance.

        Raises ``ValueError`` if the record does not exist.
        """
        record = await self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"InterviewRecord {record_id!r} not found")
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    # ── List / Count ──────────────────────────────────────────────────────

    async def list_by_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[InterviewRecord]:
        """Return a paginated list of non-deleted records for a user."""
        stmt = (
            select(InterviewRecord)
            .where(
                InterviewRecord.created_by == user_id,
                InterviewRecord.deleted_at.is_(None),
            )
            .order_by(InterviewRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """Return the count of non-deleted records for a user."""
        stmt = (
            select(func.count())
            .select_from(InterviewRecord)
            .where(
                InterviewRecord.created_by == user_id,
                InterviewRecord.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── Delete ────────────────────────────────────────────────────────────

    async def soft_delete(self, record_id: str) -> None:
        """Mark an interview record as deleted by setting ``deleted_at``."""
        record = await self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"InterviewRecord {record_id!r} not found")
        record.deleted_at = datetime.now(UTC)
        await self.db.flush()
