"""Repository for UploadedFile database operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import UploadedFile


class FileRepository:
    """Encapsulates all database access for :class:`UploadedFile`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(self, file_id: str) -> UploadedFile | None:
        """Return a single uploaded file by id, excluding soft-deleted."""
        stmt = select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    async def create(self, **kwargs) -> UploadedFile:
        """Create a new uploaded file record from keyword arguments."""
        file = UploadedFile(**kwargs)
        self.db.add(file)
        await self.db.flush()
        await self.db.refresh(file)
        return file

    # ── Delete ────────────────────────────────────────────────────────────

    async def soft_delete(self, file_id: str) -> None:
        """Mark an uploaded file as deleted by setting ``deleted_at``."""
        file = await self.get_by_id(file_id)
        if file is None:
            raise ValueError(f"UploadedFile {file_id!r} not found")
        file.deleted_at = datetime.now(UTC)
        await self.db.flush()
