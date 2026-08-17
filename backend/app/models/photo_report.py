"""photo_reports / photo_report_images 模型，列定义以 DATABASE.md 为准。"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UTCDateTime, new_uuid, utc_now
from app.models.inspection import RECORD_STATUSES, _in_clause


class PhotoReport(Base):
    __tablename__ = "photo_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String, nullable=True)
    violation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_tasks.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    images: Mapped[list["PhotoReportImage"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="PhotoReportImage.sort_order",
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_in_clause(RECORD_STATUSES)})", name="ck_photo_reports_status"
        ),
        Index("ix_photo_reports_created_by", "created_by"),
    )


class PhotoReportImage(Base):
    __tablename__ = "photo_report_images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    photo_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("photo_reports.id"), nullable=False
    )
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    frame_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_address: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_violation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    report: Mapped[PhotoReport] = relationship(back_populates="images")
