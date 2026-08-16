"""Model routing: resolve the active model per capability.

Priority: active ModelConfiguration (DB) -> environment variable fallback.
Results are cached briefly to avoid per-call DB hits.
"""
from __future__ import annotations

from app.core.cache import ttl_cache
from app.core.config import get_settings

_ENV_FALLBACK = {
    "llm": "LLM_MODEL",
    "vision": "VISION_MODEL",
    "ocr": "OCR_MODEL",
    "speech": "SPEECH_MODEL",
    "embedding": "EMBEDDING_MODEL",
    "reranker": "RERANK_MODEL",
}


@ttl_cache(seconds=30)
def resolve_model(kind: str) -> str | None:
    if kind not in _ENV_FALLBACK:
        return None
    try:
        from app.core.database import SessionLocal
        from app.models.aiplatform import ModelConfiguration
        from sqlalchemy import select

        with SessionLocal() as db:
            cfg = db.scalar(
                select(ModelConfiguration).where(
                    ModelConfiguration.kind == kind, ModelConfiguration.is_active.is_(True)
                )
            )
            if cfg is not None:
                return cfg.model_name
    except Exception:  # noqa: BLE001 - routing must never break the request
        pass
    return getattr(get_settings(), _ENV_FALLBACK[kind], None)
