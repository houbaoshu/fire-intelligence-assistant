"""RAG-specific reranking wrapper for improving retrieval relevance.

Delegates to the core AI reranker service and adapts its interface for
the RAG pipeline.
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGReranker:
    """Rerank retrieved chunks for better relevance.

    Wraps the core ``RerankerService`` to provide a RAG-oriented
    interface that preserves chunk metadata through the reranking step.
    """

    def __init__(self) -> None:
        from app.services.ai.reranker import RerankerService

        self.reranker_service = RerankerService()

    async def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Rerank chunks by relevance to the query.

        Each chunk dict is expected to contain at least a ``text`` key.
        After reranking, a ``relevance_score`` key is added (or updated)
        on each returned chunk.

        Args:
            query: The original search query.
            chunks: Retrieved chunks to rerank.
            top_k: Maximum number of results to return.

        Returns:
            Reranked list of chunk dicts with ``relevance_score``,
            ordered by descending relevance.  Returns the original
            ordering (truncated to *top_k*) if the reranker service
            fails.
        """
        if not chunks:
            return []

        logger.info(
            "Reranking chunks",
            extra={
                "query_length": len(query),
                "chunk_count": len(chunks),
                "top_k": top_k,
            },
        )

        try:
            results = await self.reranker_service.rerank(
                query=query,
                documents=chunks,
                top_k=top_k,
            )
        except Exception as exc:
            logger.warning(
                "Reranker failed, returning original order: %s",
                exc,
            )
            # Fallback: return original chunks truncated to top_k
            return chunks[:top_k]

        return results
