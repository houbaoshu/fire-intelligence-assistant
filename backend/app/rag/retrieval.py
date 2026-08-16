"""Retrieval pipeline: embed query -> permission-scoped search -> optional rerank.

The pipeline must never skip retrieval when RAG is enabled; LLM answers are
always grounded in retrieved chunks.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ai.embedding import EmbeddingService
from app.services.ai.reranker import RerankerService
from app.rag.vectorstore.base import SearchHit
from app.rag.vectorstore.factory import get_vector_store

logger = get_logger("rag.retrieval")


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        reranker_service: RerankerService | None = None,
    ):
        self.embedding = embedding_service or EmbeddingService()
        self.reranker = reranker_service or RerankerService()
        self.store = get_vector_store()

    def search(self, query: str, *, document_ids: list[str] | None = None) -> list[SearchHit]:
        """Search chunks, filtered to the given document ids (permission scope).

        document_ids=None means all documents (admin-level scope).
        """
        settings = get_settings()
        top_k = settings.RAG_TOP_K
        query_embedding = self.embedding.embed([query])[0]
        hits = self.store.search(query_embedding, top_k, document_ids=document_ids)
        if not hits:
            return []

        scores = self.reranker.rerank(query, [h.text for h in hits], top_n=settings.RAG_RERANK_TOP_K)
        if scores is not None:
            indexed = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)
            reranked = []
            for i in indexed:
                hit = hits[i]
                hit.score = scores[i]
                reranked.append(hit)
            hits = reranked
        return hits
