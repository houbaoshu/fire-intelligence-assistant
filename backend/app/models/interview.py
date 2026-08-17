"""interview_records 模型，列定义以 DATABASE.md 为准。"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONVariant, UTCDateTime, new_uuid, utc_now
from app.models.inspection import RECORD_STATUSES, _in_clause


class InterviewRecord(Base):
    __tablename__ = "interview_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    interviewee_name: Mapped[str | None] = mapped_column(String, nullable=True)
    interviewer_names: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_content: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_tasks.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_in_clause(RECORD_STATUSES)})", name="ck_interview_records_status"
        ),
        Index("ix_interview_records_created_by", "created_by"),
    )
