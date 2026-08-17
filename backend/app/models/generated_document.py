"""generated_documents 模型：版本化生成文档元数据，列定义以 DATABASE.md 为准。

约束：不得覆盖已定稿的历史文档版本；重新生成时 version 递增（见
app/services/documents/）。
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UTCDateTime, new_uuid, utc_now

DOCUMENT_TYPES = (
    "inspection_record_docx",
    "photo_report_docx",
    "interview_record_docx",
    "inspection_record_pdf",
    "photo_report_pdf",
    "interview_record_pdf",
)

SOURCE_ENTITY_TYPES = ("inspection_record", "photo_report", "interview_record")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_by_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_tasks.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            f"document_type IN ({', '.join(repr(t) for t in DOCUMENT_TYPES)})",
            name="ck_generated_documents_document_type",
        ),
        CheckConstraint(
            f"source_entity_type IN ({', '.join(repr(t) for t in SOURCE_ENTITY_TYPES)})",
            name="ck_generated_documents_source_entity_type",
        ),
        Index(
            "ix_generated_documents_source_entity",
            "source_entity_type",
            "source_entity_id",
        ),
    )
