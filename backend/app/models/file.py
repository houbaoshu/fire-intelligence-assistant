"""uploaded_files table (file metadata; binaries live in object storage)."""
from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class UploadedFile(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("ix_uploaded_files_uploaded_by", "uploaded_by"),
        Index("ix_uploaded_files_checksum", "checksum"),
    )

    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
