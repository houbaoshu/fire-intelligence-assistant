"""Vector store factory."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings

from .base import VectorStore


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    if settings.VECTOR_STORE_PROVIDER == "chroma":
        from .chroma import ChromaVectorStore

        return ChromaVectorStore()
    from .local import LocalVectorStore

    return LocalVectorStore()
