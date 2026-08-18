"""Embedding 能力服务（OpenAI 兼容 embeddings API）。

职责：仅生成检索用向量（AI_CONTEXT.md「Embedding Model」），不用于生成。
"""

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import resolve_capability_config

# 单次请求的最大文本条数。部分 OpenAI 兼容服务（如 DashScope）限制批量
# 上限（10~20 条），超限直接返回 400，因此统一按小批量分批调用。
_EMBED_BATCH_SIZE = 10


class EmbeddingService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
        session: Session | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        config = (
            None
            if client is not None
            else resolve_capability_config("embedding", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_EMBEDDING_MODEL
        self._client = client or (
            OpenAICompatClient(
                base_url=config.base_url,
                api_key=config.api_key,
                settings=self._settings,
                transport=transport,
            )
            if config
            else None
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """为文本列表生成向量；顺序与输入一致。失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("embedding")
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            vectors.extend(self._embed_batch(texts[start : start + _EMBED_BATCH_SIZE]))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        data = self._client.post_json(
            "/embeddings",
            {"model": self._model, "input": texts},
        )
        try:
            items = sorted(data["data"], key=lambda item: item["index"])
            vectors = [[float(v) for v in item["embedding"]] for item in items]
        except (KeyError, TypeError, ValueError):
            raise ai_service_error("AI 能力 embedding 返回了无法解析的响应")
        if len(vectors) != len(texts):
            raise ai_service_error("AI 能力 embedding 返回的向量数量与输入不一致")
        return vectors
