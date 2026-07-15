"""UploadedFile model — metadata for files stored in object storage."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    category: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # video / image / audio / document / template / generated_document / knowledge_source
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    uploader: Mapped["User"] = relationship(  # noqa: F821
        back_populates="uploaded_files"
    )
    photo_report_images: Mapped[list["PhotoReportImage"]] = relationship(  # noqa: F821
        back_populates="uploaded_file", lazy="noload"
    )
    generated_document: Mapped["GeneratedDocument | None"] = relationship(  # noqa: F821
        back_populates="uploaded_file", uselist=False, lazy="selectin"
    )
    knowledge_document: Mapped["KnowledgeDocument | None"] = relationship(  # noqa: F821
        back_populates="uploaded_file", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<UploadedFile id={self.id} original_name={self.original_name!r} "
            f"category={self.category!r}>"
        )
