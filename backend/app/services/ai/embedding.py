"""Text embedding service for vector representations."""

from __future__ import annotations

import openai

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Text embedding service using OpenAI-compatible API.

    Generates dense vector representations of text for semantic search
    and RAG retrieval.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise AppException(
                "AI service is not configured. Please set OPENAI_API_KEY.",
                details={"code": "AI_NOT_CONFIGURED"},
            )
        self._client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        self._model = settings.embedding_model

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        logger.info("Embedding request", extra={"model": self._model, "text_length": len(text)})

        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors in the same order.
        """
        if not texts:
            return []

        logger.info(
            "Batch embedding request",
            extra={"model": self._model, "count": len(texts)},
        )

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        # Sort by index to preserve order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
