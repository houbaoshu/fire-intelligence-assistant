"""Repository for PhotoReport and PhotoReportImage operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.photo_report import PhotoReport, PhotoReportImage


class PhotoReportRepository:
    """Encapsulates all database access for :class:`PhotoReport`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(self, report_id: str) -> PhotoReport | None:
        """Return a single photo report by id, excluding soft-deleted."""
        stmt = select(PhotoReport).where(
            PhotoReport.id == report_id,
            PhotoReport.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_images(self, report_id: str) -> PhotoReport | None:
        """Return a photo report with its images eagerly loaded."""
        stmt = (
            select(PhotoReport)
            .where(
                PhotoReport.id == report_id,
                PhotoReport.deleted_at.is_(None),
            )
            .options(selectinload(PhotoReport.images))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create / Update ───────────────────────────────────────────────────

    async def create(self, **kwargs) -> PhotoReport:
        """Create a new photo report from keyword arguments."""
        report = PhotoReport(**kwargs)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def update(self, report_id: str, **kwargs) -> PhotoReport:
        """Update an existing photo report and return the refreshed instance.

        Raises ``ValueError`` if the report does not exist.
        """
        report = await self.get_by_id(report_id)
        if report is None:
            raise ValueError(f"PhotoReport {report_id!r} not found")
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        report.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def update_images(self, report_id: str, images: list[dict]) -> list[PhotoReportImage]:
        """Replace all images for the given photo report.

        Existing images are deleted and new ones created from *images* dicts.
        Returns the newly created image instances.
        """
        report = await self.get_with_images(report_id)
        if report is None:
            raise ValueError(f"PhotoReport {report_id!r} not found")

        # Remove existing images
        for existing in list(report.images):
            await self.db.delete(existing)
        await self.db.flush()

        # Create new images
        new_images: list[PhotoReportImage] = []
        for idx, image_data in enumerate(images):
            image = PhotoReportImage(
                photo_report_id=report_id,
                sort_order=image_data.get("sort_order", idx),
                **{k: v for k, v in image_data.items() if k != "sort_order"},
            )
            self.db.add(image)
            new_images.append(image)

        await self.db.flush()
        for image in new_images:
            await self.db.refresh(image)
        return new_images

    # ── List / Count ──────────────────────────────────────────────────────

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> list[PhotoReport]:
        """Return a paginated list of non-deleted reports for a user."""
        stmt = (
            select(PhotoReport)
            .where(
                PhotoReport.created_by == user_id,
                PhotoReport.deleted_at.is_(None),
            )
            .order_by(PhotoReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """Return the count of non-deleted reports for a user."""
        stmt = (
            select(func.count())
            .select_from(PhotoReport)
            .where(
                PhotoReport.created_by == user_id,
                PhotoReport.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── Delete ────────────────────────────────────────────────────────────

    async def soft_delete(self, report_id: str) -> None:
        """Mark a photo report as deleted by setting ``deleted_at``."""
        report = await self.get_by_id(report_id)
        if report is None:
            raise ValueError(f"PhotoReport {report_id!r} not found")
        report.deleted_at = datetime.now(UTC)
        await self.db.flush()
