"""interview_records table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin, JSONBType


class InterviewRecord(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "interview_records"
    __table_args__ = (Index("ix_interview_records_created_by", "created_by"),)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interviewee_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interviewer_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_content: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
