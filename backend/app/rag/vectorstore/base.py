"""Vector store interface.

Only retrieval data lives here — business data always lives in PostgreSQL.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredChunk:
    chunk_id: str
    document_id: str
    text: str
    embedding: list[float]
    metadata: dict


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    text: str
    metadata: dict
    score: float


class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, chunks: list[StoredChunk]) -> int:
        """Insert or replace chunks; returns the number of chunks written."""

    @abstractmethod
    def delete_document(self, document_id: str) -> int:
        """Remove all chunks of a document; returns count removed."""

    @abstractmethod
    def delete_all(self) -> int:
        """Remove every chunk; returns count removed."""

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int, *, document_ids: list[str] | None = None) -> list[SearchHit]:
        """Cosine-similarity search, optionally restricted to documents."""

    @abstractmethod
    def count_chunks(self) -> int:
        """Total number of chunks in the store."""

    @abstractmethod
    def count_chunks_for(self, document_id: str) -> int:
        """Number of chunks belonging to a document."""

