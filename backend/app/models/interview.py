"""InterviewRecord model."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class InterviewRecord(Base):
    __tablename__ = "interview_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    interviewee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    interviewer_names: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_content: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
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
        back_populates="interview_records"
    )
    source_task: Mapped["AITask | None"] = relationship(  # noqa: F821
        back_populates="interview_records", foreign_keys=[source_task_id]
    )

    def __repr__(self) -> str:
        return f"<InterviewRecord id={self.id} title={self.title!r} status={self.status!r}>"
