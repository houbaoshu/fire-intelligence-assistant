"""RAG-specific embedding service wrapping the core AI embedding service.

Adds batch embedding of document chunks with progress tracking and
error handling tailored for the RAG pipeline.
"""

from __future__ import annotations

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGEmbeddingService:
    """Wraps the AI embedding service for RAG-specific operations.

    Provides batch embedding of document chunks, adding the resulting
    vectors directly into each chunk dict for downstream storage.
    """

    def __init__(self) -> None:
        from app.services.ai.embedding import EmbeddingService

        self.embedding_service = EmbeddingService()

    async def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """Embed a list of chunks, adding embedding vectors to each.

        Each chunk dict must contain a ``text`` key.  After processing,
        an ``embedding`` key is added containing the vector.

        Args:
            chunks: List of chunk dicts with at least a ``text`` key.

        Returns:
            The same list of chunk dicts, each augmented with an
            ``embedding`` key.

        Raises:
            AppException: If the embedding service is not configured or
                the embedding request fails.
        """
        if not chunks:
            return []

        texts = [c.get("text", "") for c in chunks]

        logger.info(
            "Embedding chunks",
            extra={"count": len(texts)},
        )

        try:
            embeddings = await self.embedding_service.embed_batch(texts)
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            raise AppException(
                "Failed to generate embeddings for document chunks",
                details={"code": "EMBEDDING_FAILED", "original_error": str(exc)},
            ) from exc

        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        return chunks

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for retrieval.

        Args:
            query: The search query text.

        Returns:
            Embedding vector for the query.
        """
        logger.info("Embedding query", extra={"query_length": len(query)})
        return await self.embedding_service.embed_text(query)
