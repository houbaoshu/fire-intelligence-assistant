"""knowledge_documents and knowledge_index_jobs tables."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin, JSONBType


class KnowledgeDocument(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class KnowledgeIndexJob(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_index_jobs"

    knowledge_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    ai_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    indexed_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
