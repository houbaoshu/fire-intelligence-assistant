"""ai_tasks table (async AI processing tasks)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPkMixin, JSONBType


class AiTask(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ai_tasks"

    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # workflow bookkeeping (not part of DATABASE.md public columns; internal)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
