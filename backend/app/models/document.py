"""GeneratedDocument model — tracks generated Word/PDF outputs."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # inspection_record_docx / photo_report_docx / interview_record_docx / ..._pdf
    source_entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # inspection_record / photo_report / interview_record
    source_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    uploaded_file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_by_task_id: Mapped[str | None] = mapped_column(
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

    # ── Relationships ─────────────────────────────────────────
    uploaded_file: Mapped["UploadedFile"] = relationship(  # noqa: F821
        back_populates="generated_document"
    )
    generated_by_task: Mapped["AITask | None"] = relationship(  # noqa: F821
        back_populates="generated_documents", foreign_keys=[generated_by_task_id]
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="generated_documents"
    )

    def __repr__(self) -> str:
        return (
            f"<GeneratedDocument id={self.id} document_type={self.document_type!r} "
            f"version={self.version}>"
        )
