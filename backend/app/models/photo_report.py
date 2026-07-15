"""PhotoReport and PhotoReportImage models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class PhotoReport(Base):
    __tablename__ = "photo_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inspection_unit: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inspection_address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    violation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )  # draft / processing / generated / reviewed / finalized / archived / failed
    source_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="photo_reports"
    )
    source_task: Mapped["AITask | None"] = relationship(  # noqa: F821
        back_populates="photo_reports", foreign_keys=[source_task_id]
    )
    images: Mapped[list["PhotoReportImage"]] = relationship(
        back_populates="photo_report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PhotoReport id={self.id} title={self.title!r} status={self.status!r}>"


class PhotoReportImage(Base):
    __tablename__ = "photo_report_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    photo_report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("photo_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frame_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_address: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    detected_violation: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # ── Relationships ─────────────────────────────────────────
    photo_report: Mapped["PhotoReport"] = relationship(back_populates="images")
    uploaded_file: Mapped["UploadedFile"] = relationship(  # noqa: F821
        back_populates="photo_report_images"
    )

    def __repr__(self) -> str:
        return (
            f"<PhotoReportImage id={self.id} photo_report_id={self.photo_report_id} "
            f"is_selected={self.is_selected}>"
        )
