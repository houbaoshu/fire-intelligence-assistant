"""uploaded_files 模型：上传文件元数据。列定义以 DATABASE.md 为准。

文件本体存对象存储（见 app/services/storage/），本表只存元数据与存储路径。
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UTCDateTime, new_uuid, utc_now

FILE_CATEGORIES = (
    "video",
    "image",
    "audio",
    "document",
    "template",
    "generated_document",
    "knowledge_source",
)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    storage_provider: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"category IN ({', '.join(repr(c) for c in FILE_CATEGORIES)})",
            name="ck_uploaded_files_category",
        ),
        Index("ix_uploaded_files_uploaded_by", "uploaded_by"),
        Index("ix_uploaded_files_checksum", "checksum"),
    )
