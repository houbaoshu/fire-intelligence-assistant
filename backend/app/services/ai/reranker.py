"""Reranker 能力服务（Jina/Cohere 风格 rerank API，经 OpenAI 兼容网关暴露）。

职责：在上下文送入 LLM 之前提升检索质量（AI_CONTEXT.md「Reranker」）。
仅在配置后使用（providers.py 模型路由解析）；未配置时由 ``app/rag/reranking/`` 提供确定性本地回退。
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


class RerankerService:
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
            else resolve_capability_config("reranker", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_RERANKER_MODEL
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

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def rerank(
        self, query: str, documents: list[str], *, top_n: int
    ) -> list[tuple[int, float]]:
        """返回 (输入下标, 相关性分数) 列表，按分数降序。失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("reranker")
        if not documents:
            return []
        data = self._client.post_json(
            "/rerank",
            {
                "model": self._model,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(documents)),
            },
        )
        try:
            results = [
                (int(item["index"]), float(item["relevance_score"]))
                for item in data["results"]
            ]
        except (KeyError, TypeError, ValueError):
            raise ai_service_error("AI 能力 reranker 返回了无法解析的响应")
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_n]
