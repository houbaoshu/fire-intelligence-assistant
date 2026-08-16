"""Embedding service: vector embeddings for retrieval."""
from __future__ import annotations

from app.core.config import get_settings

from .client import AIProviderClient


class EmbeddingService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def model(self) -> str | None:
        from app.services.aiplatform.router import resolve_model

        return resolve_model("embedding")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.client.embeddings(self.model or "", texts)
