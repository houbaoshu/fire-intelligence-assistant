"""Embedding 能力服务（OpenAI 兼容 embeddings API）。

职责：仅生成检索用向量（AI_CONTEXT.md「Embedding Model」），不用于生成。
"""

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import AIProviders


class EmbeddingService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or (
            OpenAICompatClient(
                base_url=self._settings.AI_EMBEDDING_BASE_URL,
                api_key=self._settings.AI_EMBEDDING_API_KEY,
                settings=self._settings,
                transport=transport,
            )
            if AIProviders(self._settings).is_configured("embedding")
            else None
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """为文本列表生成向量；顺序与输入一致。失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("embedding")
        if not texts:
            return []
        data = self._client.post_json(
            "/embeddings",
            {"model": self._settings.AI_EMBEDDING_MODEL, "input": texts},
        )
        try:
            items = sorted(data["data"], key=lambda item: item["index"])
            vectors = [[float(v) for v in item["embedding"]] for item in items]
        except (KeyError, TypeError, ValueError):
            raise ai_service_error("AI 能力 embedding 返回了无法解析的响应")
        if len(vectors) != len(texts):
            raise ai_service_error("AI 能力 embedding 返回的向量数量与输入不一致")
        return vectors
