"""KnowledgeDocument and KnowledgeIndexJob models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded", index=True
    )  # uploaded / parsing / indexing / indexed / failed / outdated
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(300), nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_: Mapped[dict | list | None] = mapped_column("metadata", JSON, nullable=True)
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
    uploaded_file: Mapped["UploadedFile"] = relationship(  # noqa: F821
        back_populates="knowledge_document"
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="knowledge_documents"
    )
    index_jobs: Mapped[list["KnowledgeIndexJob"]] = relationship(
        back_populates="knowledge_document",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id} title={self.title!r} status={self.status!r}>"


class KnowledgeIndexJob(Base):
    __tablename__ = "knowledge_index_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    knowledge_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ai_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # index / reindex / delete_index / full_rebuild
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending / processing / completed / failed
    indexed_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    knowledge_document: Mapped["KnowledgeDocument | None"] = relationship(
        back_populates="index_jobs"
    )
    ai_task: Mapped["AITask | None"] = relationship(  # noqa: F821
        back_populates="knowledge_index_jobs"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeIndexJob id={self.id} action={self.action!r} status={self.status!r}>"
