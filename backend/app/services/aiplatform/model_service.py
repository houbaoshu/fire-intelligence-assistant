"""Model configuration & routing service.

Model names are resolved through active ModelConfiguration rows, falling back
to environment variables (legacy). This keeps providers swappable without
touching business code.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.aiplatform import ModelConfiguration

KINDS = ("llm", "vision", "ocr", "speech", "embedding", "reranker")

_ENV_FALLBACK = {
    "llm": "LLM_MODEL",
    "vision": "VISION_MODEL",
    "ocr": "OCR_MODEL",
    "speech": "SPEECH_MODEL",
    "embedding": "EMBEDDING_MODEL",
    "reranker": "RERANK_MODEL",
}


class ModelService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, kind: str | None = None) -> list[ModelConfiguration]:
        stmt = select(ModelConfiguration).order_by(ModelConfiguration.kind, ModelConfiguration.priority.desc())
        if kind:
            stmt = stmt.where(ModelConfiguration.kind == kind)
        return list(self.db.scalars(stmt).all())

    def create(self, actor, *, name: str, kind: str, model_name: str, provider: str = "openai-compatible", base_url: str | None = None, api_key_ref: str | None = None, priority: int = 0) -> ModelConfiguration:
        if kind not in KINDS:
            raise ValidationError(f"非法能力类型:{kind}")
        cfg = ModelConfiguration(
            name=name.strip(), kind=kind, provider=provider,
            model_name=model_name.strip(), base_url=base_url,
            api_key_ref=api_key_ref, priority=priority, is_active=True,
        )
        self.db.add(cfg)
        self.db.commit()
        return cfg

    def set_active(self, actor, config_id: uuid.UUID | str) -> ModelConfiguration:
        cfg = self.db.get(ModelConfiguration, uuid.UUID(str(config_id)))
        if cfg is None:
            raise NotFoundError("模型配置不存在")
        # deactivate others of the same kind
        for other in self.db.scalars(select(ModelConfiguration).where(ModelConfiguration.kind == cfg.kind)).all():
            other.is_active = False
        cfg.is_active = True
        self.db.commit()
        return cfg

    def delete(self, actor, config_id: uuid.UUID | str) -> None:
        cfg = self.db.get(ModelConfiguration, uuid.UUID(str(config_id)))
        if cfg is None:
            raise NotFoundError("模型配置不存在")
        self.db.delete(cfg)
        self.db.commit()

    def resolve_model(self, kind: str) -> str | None:
        """Resolve the active model name for a capability (DB first, env fallback)."""
        if kind not in KINDS:
            return None
        cfg = self.db.scalar(
            select(ModelConfiguration).where(
                ModelConfiguration.kind == kind, ModelConfiguration.is_active.is_(True)
            )
        )
        if cfg is not None:
            return cfg.model_name
        env_var = _ENV_FALLBACK[kind]
        return getattr(get_settings(), env_var, None)
