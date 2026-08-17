"""ai_tasks 模型：异步 AI 处理任务。列定义与枚举以 DATABASE.md 为准。"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONVariant, UTCDateTime, new_uuid, utc_now

TASK_STATUSES = ("pending", "queued", "processing", "completed", "failed", "cancelled")
TASK_TYPES = (
    "inspection_record_generation",
    "photo_report_generation",
    "interview_record_generation",
    "speech_transcription",
    "video_analysis",
    "document_generation",
    "knowledge_indexing",
    "knowledge_reindexing",
)

# 终态：到达后前端必须停止轮询（API.md §8）
TERMINAL_STATUSES = ("completed", "failed", "cancelled")
# 允许重试 / 取消的状态（API.md §8）
RETRYABLE_STATUSES = ("failed", "cancelled")
CANCELLABLE_STATUSES = ("pending", "queued", "processing")


class AITask(Base):
    __tablename__ = "ai_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    # 执行追踪（M5）：retry 创建新实例并递增 attempt_count，原任务 id 记入 input_data.retry_of
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    # 幂等提交（M5）：(created_by, task_type, idempotency_key) 唯一
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in TASK_STATUSES)})",
            name="ck_ai_tasks_status",
        ),
        CheckConstraint(
            f"task_type IN ({', '.join(repr(t) for t in TASK_TYPES)})",
            name="ck_ai_tasks_task_type",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_ai_tasks_progress"),
        CheckConstraint("attempt_count >= 1", name="ck_ai_tasks_attempt_count"),
        Index("ix_ai_tasks_status", "status"),
        Index("ix_ai_tasks_task_type", "task_type"),
        Index("ix_ai_tasks_created_by_status_created_at", "created_by", "status", "created_at"),
        Index("ix_ai_tasks_lease_expires_at", "lease_expires_at"),
        Index(
            "ux_ai_tasks_idempotency",
            "created_by",
            "task_type",
            "idempotency_key",
            unique=True,
        ),
    )
