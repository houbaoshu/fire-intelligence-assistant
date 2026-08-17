"""knowledge_documents / knowledge_index_jobs 模型。列定义与枚举以 DATABASE.md 为准。

注意：附加元数据列名为 ``doc_metadata``（而非 ``metadata``），避免与
SQLAlchemy Declarative 保留属性冲突（DATABASE.md knowledge_documents 约束）。
"""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONVariant, UTCDateTime, new_uuid, utc_now

# knowledge_documents.status（DATABASE.md）
DOCUMENT_STATUSES = ("uploaded", "parsing", "indexing", "indexed", "failed", "outdated")
# 索引进行中（未完成）的状态集合，用于聚合统计
INDEXING_STATUSES = ("uploaded", "parsing", "indexing")

# knowledge_index_jobs.action（DATABASE.md）
JOB_ACTIONS = ("index", "reindex", "delete_index", "full_rebuild")
# knowledge_index_jobs.status（DATABASE.md 未定义枚举，与 ai_tasks 状态机对齐）
JOB_STATUSES = ("pending", "processing", "completed", "failed", "cancelled")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    document_type: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="uploaded")
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in DOCUMENT_STATUSES)})",
            name="ck_knowledge_documents_status",
        ),
        Index("ix_knowledge_documents_status", "status"),
        Index("ix_knowledge_documents_checksum", "checksum"),
    )


class KnowledgeIndexJob(Base):
    __tablename__ = "knowledge_index_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    knowledge_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_documents.id"), nullable=True
    )
    ai_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_tasks.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    indexed_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"action IN ({', '.join(repr(a) for a in JOB_ACTIONS)})",
            name="ck_knowledge_index_jobs_action",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in JOB_STATUSES)})",
            name="ck_knowledge_index_jobs_status",
        ),
        Index("ix_knowledge_index_jobs_document", "knowledge_document_id"),
        Index("ix_knowledge_index_jobs_ai_task", "ai_task_id"),
    )
