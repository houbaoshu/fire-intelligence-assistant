"""AI 能力配置探测与模型路由（M8）。

能力（capability）取值：``llm`` / ``vision`` / ``ocr`` / ``speech`` /
``embedding`` / ``reranker``。

配置解析顺序（``resolve_capability_config``，改动集中于本工厂层，业务代码
不感知来源）：

1. 数据库 ``model_configurations``：该 kind 的生效配置（``is_active``，按
   ``priority`` 升序）取第一条可完整解析的；``api_key_ref`` 只存密钥环境
   变量名，密钥从该环境变量解析（不落库、不落日志）；``base_url`` 为空时
   回退该 kind 的环境变量 Base URL。
2. 回退环境变量 ``AI_{KIND}_API_KEY`` / ``AI_{KIND}_MODEL`` /
   ``AI_{KIND}_BASE_URL``（M1–M7 现状逻辑）。

真实 client 见同目录 ``llm.py`` / ``vision.py`` / ``ocr.py`` / ``speech.py`` /
``embedding.py`` / ``reranker.py``（OpenAI 兼容 HTTP API）。
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger("ai.providers")

CAPABILITIES = ("llm", "vision", "ocr", "speech", "embedding", "reranker")

# capability → (base_url, api_key, model) 环境变量字段名
_ENV_FIELDS: dict[str, tuple[str, str, str]] = {
    "llm": ("AI_LLM_BASE_URL", "AI_LLM_API_KEY", "AI_LLM_MODEL"),
    "vision": ("AI_VISION_BASE_URL", "AI_VISION_API_KEY", "AI_VISION_MODEL"),
    "ocr": ("AI_OCR_BASE_URL", "AI_OCR_API_KEY", "AI_OCR_MODEL"),
    "speech": ("AI_SPEECH_BASE_URL", "AI_SPEECH_API_KEY", "AI_SPEECH_MODEL"),
    "embedding": (
        "AI_EMBEDDING_BASE_URL",
        "AI_EMBEDDING_API_KEY",
        "AI_EMBEDDING_MODEL",
    ),
    "reranker": (
        "AI_RERANKER_BASE_URL",
        "AI_RERANKER_API_KEY",
        "AI_RERANKER_MODEL",
    ),
}


@dataclass(frozen=True)
class CapabilityConfig:
    """一次解析得到的能力配置；source 标记来源（database / environment）。"""

    provider: str
    model: str
    base_url: str
    api_key: str
    source: str


def env_capability_config(
    capability: str, settings: Settings | None = None
) -> CapabilityConfig | None:
    """环境变量配置（M1–M7 现状逻辑）；三项齐全才算已配置。"""
    if capability not in _ENV_FIELDS:
        raise ValueError(f"未知 AI 能力: {capability}")
    s = settings or get_settings()
    base_field, key_field, model_field = _ENV_FIELDS[capability]
    base_url = getattr(s, base_field)
    api_key = getattr(s, key_field)
    model = getattr(s, model_field)
    if not (base_url and api_key and model):
        return None
    return CapabilityConfig(
        provider="env", model=model, base_url=base_url, api_key=api_key,
        source="environment",
    )


def _db_capability_config(
    capability: str, settings: Settings, session: Session | None
) -> CapabilityConfig | None:
    """数据库生效配置：按 priority 升序取第一条可完整解析的，其余跳过。"""
    from app.db import SessionLocal
    from app.models.ai_platform import ModelConfiguration

    try:
        if session is not None:
            rows = _active_rows(session, capability)
        else:
            with SessionLocal() as own_session:
                rows = _active_rows(own_session, capability)
    except SQLAlchemyError as exc:
        logger.info(
            "模型配置查询失败（回退环境变量）: capability=%s %s",
            capability, type(exc).__name__,
        )
        return None
    key_field = _ENV_FIELDS[capability][1]
    base_field = _ENV_FIELDS[capability][0]
    for row in rows:
        # api_key_ref 只存环境变量名；密钥从此处唯一入口解析，绝不入库/日志
        api_key = (
            os.environ.get(row.api_key_ref, "")
            if row.api_key_ref
            else getattr(settings, key_field)
        )
        base_url = row.base_url or getattr(settings, base_field)
        if api_key and base_url and row.model_name:
            return CapabilityConfig(
                provider=row.provider,
                model=row.model_name,
                base_url=base_url,
                api_key=api_key,
                source="database",
            )
        logger.info(
            "模型配置 %s（%s）解析不完整（缺 api_key/base_url/model），跳过",
            row.name, capability,
        )
    return None


def _active_rows(session: Session, capability: str):
    from app.models.ai_platform import ModelConfiguration

    stmt = (
        select(ModelConfiguration)
        .where(
            ModelConfiguration.kind == capability,
            ModelConfiguration.is_active.is_(True),
        )
        .order_by(ModelConfiguration.priority, ModelConfiguration.created_at)
    )
    return list(session.execute(stmt).scalars().all())


def resolve_capability_config(
    capability: str,
    settings: Settings | None = None,
    session: Session | None = None,
) -> CapabilityConfig | None:
    """模型路由入口：DB 生效配置优先，回退环境变量。"""
    s = settings or get_settings()
    config = _db_capability_config(capability, s, session)
    if config is not None:
        return config
    return env_capability_config(capability, s)


class AIProviders:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self, capability: str, session: Session | None = None) -> bool:
        return (
            resolve_capability_config(capability, settings=self._settings, session=session)
            is not None
        )

    def missing(self, capabilities: tuple[str, ...]) -> list[str]:
        return [c for c in capabilities if not self.is_configured(c)]


@lru_cache
def get_ai_providers() -> AIProviders:
    return AIProviders()
