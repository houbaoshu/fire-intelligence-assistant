"""photo_reports and photo_report_images tables."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class PhotoReport(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "photo_reports"
    __table_args__ = (Index("ix_photo_reports_created_by", "created_by"),)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    violation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    images: Mapped[list["PhotoReportImage"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="PhotoReportImage.sort_order",
    )


class PhotoReportImage(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "photo_report_images"

    photo_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("photo_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    frame_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_violation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    report: Mapped[PhotoReport] = relationship(back_populates="images")
