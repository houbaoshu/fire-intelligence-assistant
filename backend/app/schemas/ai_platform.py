"""AI 平台 schema（API.md §12，M8）。"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.ai_platform import MODEL_KINDS
from app.schemas.common import UTCModel


# ---------- Prompt 管理（§12.1） ----------


class PromptVersionItem(UTCModel):
    id: uuid.UUID
    key: str
    name: str | None
    description: str | None
    content: str
    version: int
    is_active: bool
    created_at: datetime


class PromptVersionListResponse(BaseModel):
    items: list[PromptVersionItem]


class PromptVersionCreateRequest(BaseModel):
    content: str
    name: str | None = None
    description: str | None = None

    @field_validator("content")
    @classmethod
    def _validate_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("Prompt 内容不能为空")
        return content


class PromptActivateResponse(BaseModel):
    id: uuid.UUID
    is_active: bool


# ---------- 模型管理（§12.2） ----------


class ModelConfigItem(UTCModel):
    id: uuid.UUID
    name: str
    kind: str
    provider: str
    model_name: str
    base_url: str | None
    api_key_ref: str | None
    is_active: bool
    priority: int


class ModelConfigListResponse(BaseModel):
    items: list[ModelConfigItem]


class ModelConfigCreateRequest(BaseModel):
    name: str
    kind: str
    provider: str
    model_name: str
    base_url: str | None = None
    api_key_ref: str | None = None
    is_active: bool = True
    priority: int = 100

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        if value not in MODEL_KINDS:
            raise ValueError(f"kind 必须是 {', '.join(MODEL_KINDS)} 之一")
        return value

    @field_validator("name", "provider", "model_name")
    @classmethod
    def _validate_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("字段不能为空")
        return stripped


class ModelConfigUpdateRequest(BaseModel):
    name: str | None = None
    kind: str | None = None
    provider: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key_ref: str | None = None
    is_active: bool | None = None
    priority: int | None = None

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str | None) -> str | None:
        if value is not None and value not in MODEL_KINDS:
            raise ValueError(f"kind 必须是 {', '.join(MODEL_KINDS)} 之一")
        return value


# ---------- 评估（§12.3） ----------


class EvaluationQuestion(BaseModel):
    question: str
    expected_keywords: list[str] = []
    require_source: bool = False
    expect_refusal: bool = False

    @field_validator("question")
    @classmethod
    def _validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("问题不能为空")
        return question


class EvaluationRunRequest(BaseModel):
    name: str
    questions: list[EvaluationQuestion]

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("评估名称不能为空")
        return name

    @field_validator("questions")
    @classmethod
    def _validate_questions(cls, value: list[EvaluationQuestion]) -> list[EvaluationQuestion]:
        if not value:
            raise ValueError("问题集不能为空")
        return value


class EvaluationResultItem(UTCModel):
    id: uuid.UUID
    name: str
    status: str
    total_questions: int
    passed: int
    created_at: datetime


class EvaluationDetailResponse(EvaluationResultItem):
    details: list[dict[str, Any]] | None


# ---------- 插件（§12.4） ----------


class PluginItem(UTCModel):
    id: uuid.UUID
    name: str
    version: str | None
    description: str | None
    entry_point: str
    enabled: bool


class PluginListResponse(BaseModel):
    items: list[PluginItem]


class PluginUpdateRequest(BaseModel):
    enabled: bool
