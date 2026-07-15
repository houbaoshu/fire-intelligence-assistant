"""Document reranking service for improving retrieval quality."""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class RerankerService:
    """Reranking service for improving document retrieval quality.

    Uses a cross-encoder reranker model to rescore documents against
    the query, producing a more relevant ordering than embedding
    similarity alone.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.reranker_model
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url

        if not self._api_key:
            raise AppException(
                "AI service is not configured. Please set OPENAI_API_KEY.",
                details={"code": "AI_NOT_CONFIGURED"},
            )

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Rerank documents by relevance to the query.

        Each document dict should contain at least a ``text`` key with
        the document content.  Additional keys are preserved and
        returned alongside a ``relevance_score`` key.

        Args:
            query: The search query.
            documents: List of document dicts to rerank.
            top_k: Number of top results to return.

        Returns:
            Reranked list of document dicts with ``relevance_score`` added.
        """
        if not documents:
            return []

        logger.info(
            "Reranking request",
            extra={"model": self._model, "doc_count": len(documents), "top_k": top_k},
        )

        # Use DashScope-compatible reranker API
        texts = [doc.get("text", "") for doc in documents]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/rerank"
                    if self._base_url
                    else "https://dashscope.aliyuncs.com/api/v1/services/rerank",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "input": {
                            "query": query,
                            "documents": texts,
                        },
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()

            # Parse DashScope reranker response format
            results = result.get("output", {}).get("results", [])

            # Build scored documents
            scored_docs: list[dict] = []
            for r in results:
                idx = r.get("index", 0)
                score = r.get("relevance_score", 0.0)
                doc = documents[idx].copy() if idx < len(documents) else {}
                doc["relevance_score"] = score
                scored_docs.append(doc)

            # Sort by score descending and return top_k
            scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored_docs[:top_k]

        except Exception as exc:
            logger.warning("Reranker failed, falling back to original order: %s", exc)
            # Fallback: return original documents with neutral score
            return documents[:top_k]
