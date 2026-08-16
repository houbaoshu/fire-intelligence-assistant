"""Reranker service: improves retrieval quality before LLM context building.

Optional: when no rerank model is configured, retrieval order is kept
(the flow is still Retriever -> LLM; reranking is an explicit enhancement).
"""
from __future__ import annotations

from app.core.config import get_settings

from .client import AIProviderClient


class RerankerService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def enabled(self) -> bool:
        return bool(get_settings().RERANK_MODEL)

    def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[float] | None:
        """Return relevance scores; None when reranking is not configured
        (caller keeps retrieval order in that case)."""
        if not self.enabled:
            return None
        return self.client.rerank(get_settings().RERANK_MODEL or "", query, documents, top_n)
