"""AITask model — asynchronous AI processing tasks."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class AITask(Base):
    __tablename__ = "ai_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # inspection_record_generation / photo_report_generation / ...
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending / queued / processing / completed / failed / cancelled
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    result_data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    # ── Relationships ─────────────────────────────────────────
    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="ai_tasks"
    )
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(  # noqa: F821
        back_populates="source_task", lazy="noload"
    )
    photo_reports: Mapped[list["PhotoReport"]] = relationship(  # noqa: F821
        back_populates="source_task", lazy="noload"
    )
    interview_records: Mapped[list["InterviewRecord"]] = relationship(  # noqa: F821
        back_populates="source_task", lazy="noload"
    )
    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(  # noqa: F821
        back_populates="generated_by_task", lazy="noload"
    )
    knowledge_index_jobs: Mapped[list["KnowledgeIndexJob"]] = relationship(  # noqa: F821
        back_populates="ai_task", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<AITask id={self.id} task_type={self.task_type!r} "
            f"status={self.status!r} progress={self.progress}>"
        )
