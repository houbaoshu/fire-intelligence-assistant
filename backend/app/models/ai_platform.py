"""AI 平台模型（M8）：prompt_versions / model_configurations /
evaluation_results / plugins。列定义以 DATABASE.md 对应小节为准。

安全约束：model_configurations.api_key_ref 只存密钥环境变量名，
密钥本身绝不落库（AGENTS.md 安全规则）。
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONVariant, UTCDateTime, new_uuid, utc_now

# 与 app/services/ai/providers.py CAPABILITIES 保持一致（此处独立定义避免循环导入）
MODEL_KINDS = ("llm", "vision", "ocr", "speech", "embedding", "reranker")

EVALUATION_STATUSES = ("completed", "failed")


class PromptVersion(Base):
    """版本化 Prompt 目录：每个 key 仅一个 is_active 生效版本。"""

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_prompt_versions_key_version"),
        Index("ix_prompt_versions_key", "key"),
    )


class ModelConfiguration(Base):
    """按能力类型（kind）的模型配置；模型路由优先取生效配置，回退环境变量。"""

    __tablename__ = "model_configurations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # 只存密钥环境变量名（如 MY_LLM_KEY），密钥本身从该环境变量解析
    api_key_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            f"kind IN ({', '.join(repr(k) for k in MODEL_KINDS)})",
            name="ck_model_configurations_kind",
        ),
        Index("ix_model_configurations_kind_active", "kind", "is_active"),
    )


class EvaluationResult(Base):
    """评估运行结果：真实调用 RAG+LLM 查询管线后按规则计分。"""

    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed")
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in EVALUATION_STATUSES)})",
            name="ck_evaluation_results_status",
        ),
    )


class Plugin(Base):
    """服务端插件注册表；内置插件见 app/plugins/builtin/。"""

    __tablename__ = "plugins"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_point: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (Index("ix_plugins_name", "name", unique=True),)
