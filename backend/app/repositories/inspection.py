"""Repository for InspectionRecord and InspectionRecordItem operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inspection import InspectionRecord, InspectionRecordItem


class InspectionRecordRepository:
    """Encapsulates all database access for :class:`InspectionRecord`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(
        self, record_id: str, include_deleted: bool = False
    ) -> InspectionRecord | None:
        """Return a single inspection record by id.

        By default soft-deleted records (``deleted_at IS NOT NULL``) are
        excluded.  Pass *include_deleted=True* to include them.
        """
        stmt = select(InspectionRecord).where(InspectionRecord.id == record_id)
        if not include_deleted:
            stmt = stmt.where(InspectionRecord.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_items(self, record_id: str) -> InspectionRecord | None:
        """Return an inspection record with its items eagerly loaded."""
        stmt = (
            select(InspectionRecord)
            .where(
                InspectionRecord.id == record_id,
                InspectionRecord.deleted_at.is_(None),
            )
            .options(selectinload(InspectionRecord.items))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create / Update ───────────────────────────────────────────────────

    async def create(self, **kwargs) -> InspectionRecord:
        """Create a new inspection record from keyword arguments."""
        record = InspectionRecord(**kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record_id: str, **kwargs) -> InspectionRecord:
        """Update an existing inspection record and return the refreshed instance.

        Raises ``ValueError`` if the record does not exist.
        """
        record = await self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"InspectionRecord {record_id!r} not found")
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update_items(self, record_id: str, items: list[dict]) -> list[InspectionRecordItem]:
        """Replace all items for the given inspection record.

        Existing items are deleted and new ones created from *items* dicts.
        Returns the newly created item instances.
        """
        record = await self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"InspectionRecord {record_id!r} not found")

        # Remove existing items
        for existing in list(record.items):
            await self.db.delete(existing)
        await self.db.flush()

        # Create new items
        new_items: list[InspectionRecordItem] = []
        for idx, item_data in enumerate(items):
            item = InspectionRecordItem(
                inspection_record_id=record_id,
                sort_order=item_data.get("sort_order", idx),
                **{k: v for k, v in item_data.items() if k != "sort_order"},
            )
            self.db.add(item)
            new_items.append(item)

        await self.db.flush()
        for item in new_items:
            await self.db.refresh(item)
        return new_items

    # ── List / Count ──────────────────────────────────────────────────────

    async def list_by_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[InspectionRecord]:
        """Return a paginated list of non-deleted records for a user."""
        stmt = (
            select(InspectionRecord)
            .where(
                InspectionRecord.created_by == user_id,
                InspectionRecord.deleted_at.is_(None),
            )
            .order_by(InspectionRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """Return the count of non-deleted records for a user."""
        stmt = (
            select(func.count())
            .select_from(InspectionRecord)
            .where(
                InspectionRecord.created_by == user_id,
                InspectionRecord.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── Delete ────────────────────────────────────────────────────────────

    async def soft_delete(self, record_id: str) -> None:
        """Mark an inspection record as deleted by setting ``deleted_at``."""
        record = await self.get_by_id(record_id)
        if record is None:
            raise ValueError(f"InspectionRecord {record_id!r} not found")
        record.deleted_at = datetime.now(UTC)
        await self.db.flush()
