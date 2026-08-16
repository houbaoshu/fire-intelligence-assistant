"""generated_documents table (versioned output documents)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPkMixin


class GeneratedDocument(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "generated_documents"

    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_by_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
