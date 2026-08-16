"""AI platform tables (Milestone 8).

These tables make prompts, model configs, evaluations and plugins manageable
without architectural changes (ROADMAP Milestone 8 deliverable).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPkMixin, JSONBType


class PromptVersion(UUIDPkMixin, TimestampMixin, Base):
    """Versioned prompt catalog. Seeded from app/prompts; admin-editable."""

    __tablename__ = "prompt_versions"

    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class ModelConfiguration(UUIDPkMixin, TimestampMixin, Base):
    """Named model configuration per capability kind."""

    __tablename__ = "model_configurations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # llm | vision | ocr | speech | embedding | reranker
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="openai-compatible")
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_ref: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # env var name, e.g. OPENAI_API_KEY; never store the key itself
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)


class EvaluationResult(UUIDPkMixin, TimestampMixin, Base):
    """Stored results of an evaluation run."""

    __tablename__ = "evaluation_results"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class PluginRecord(UUIDPkMixin, TimestampMixin, Base):
    """Registered plugin metadata."""

    __tablename__ = "plugins"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="0.1.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_point: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
