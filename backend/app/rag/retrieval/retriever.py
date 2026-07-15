"""Vector store retriever backed by ChromaDB.

Handles embedding, storage, and similarity search for document chunks.
Supports both local persistent storage and remote ChromaDB server.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class Retriever:
    """Retrieve relevant chunks from a ChromaDB vector store.

    The retriever lazily initialises the ChromaDB client and collection
    on first use so that import-time failures are avoided when ChromaDB
    is not installed or not reachable.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._collection: Any = None
        self._settings = get_settings()

    # ── Public API ──────────────────────────────────────────────────────

    async def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        """Retrieve top-k relevant chunks for a query.

        The query is embedded using the RAG embedding service and then
        used to perform a nearest-neighbour search against ChromaDB.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results to return.

        Returns:
            List of dicts with ``text``, ``metadata``, and ``score``
            keys, ordered by descending relevance.
        """
        from app.rag.embedding.service import RAGEmbeddingService

        collection = self._get_collection()
        embedding_service = RAGEmbeddingService()

        logger.info(
            "Retrieving chunks",
            extra={"query_length": len(query), "top_k": top_k},
        )

        try:
            query_embedding = await embedding_service.embed_query(query)
        except Exception as exc:
            logger.error("Query embedding failed: %s", exc)
            raise AppException(
                "Failed to embed search query",
                details={"code": "QUERY_EMBEDDING_FAILED"},
            ) from exc

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count() or 1),
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            raise AppException(
                "Vector store query failed",
                details={"code": "RETRIEVAL_FAILED"},
            ) from exc

        # ChromaDB returns lists of lists (one per query embedding)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks: list[dict] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append(
                {
                    "text": doc,
                    "metadata": meta or {},
                    # ChromaDB returns L2 distances; convert to a similarity
                    # score (smaller distance = higher similarity).
                    "score": 1.0 / (1.0 + dist),
                }
            )

        return chunks

    async def add_chunks(
        self,
        chunks: list[dict],
        collection_name: str | None = None,
    ) -> None:
        """Add embedded chunks to the vector store.

        Each chunk dict must contain ``text``, ``embedding``, and
        ``metadata`` keys.

        Args:
            chunks: List of embedded chunk dicts.
            collection_name: Optional override for the target collection.
                Defaults to the configured collection name.
        """
        if not chunks:
            return

        collection = self._get_collection(name=collection_name)

        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.get("text", "") for c in chunks]
        embeddings = [c.get("embedding") for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]

        logger.info(
            "Adding chunks to vector store",
            extra={"count": len(chunks), "collection": collection.name},
        )

        try:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            logger.error("Failed to add chunks to ChromaDB: %s", exc)
            raise AppException(
                "Failed to store document chunks in vector store",
                details={"code": "STORE_FAILED"},
            ) from exc

    async def delete_by_document_id(self, document_id: str) -> None:
        """Remove all chunks associated with a document.

        Args:
            document_id: Identifier of the document whose chunks should
                be removed.
        """
        collection = self._get_collection()

        logger.info(
            "Deleting chunks by document_id",
            extra={"document_id": document_id},
        )

        try:
            collection.delete(where={"document_id": document_id})
        except Exception as exc:
            logger.error("Failed to delete chunks: %s", exc)
            raise AppException(
                "Failed to delete document chunks from vector store",
                details={"code": "DELETE_FAILED"},
            ) from exc

    async def clear_collection(self) -> None:
        """Clear the entire collection for a full rebuild."""
        collection_name = self._settings.chroma_collection

        logger.info(
            "Clearing collection",
            extra={"collection": collection_name},
        )

        client = self._get_client()
        try:
            client.delete_collection(collection_name)
        except Exception:
            # Collection might not exist yet; that is fine.
            pass

        # Force re-creation on next access
        self._collection = None

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_client(self) -> Any:
        """Lazily initialise and return the ChromaDB client.

        Attempts to connect to a remote ChromaDB server first (using
        ``chromadb.HttpClient``).  If the connection fails, falls back
        to a local ``PersistentClient``.
        """
        if self._client is not None:
            return self._client

        try:
            import chromadb
        except ImportError as exc:
            raise AppException(
                "chromadb is required for RAG retrieval. Install it with: pip install chromadb",
                details={"code": "DEPENDENCY_MISSING"},
            ) from exc

        # Try remote (HTTP) client first
        try:
            self._client = chromadb.HttpClient(
                host=self._settings.chroma_host,
                port=self._settings.chroma_port,
            )
            # Verify connectivity with a heartbeat
            self._client.heartbeat()
            logger.info(
                "Connected to ChromaDB server",
                extra={
                    "host": self._settings.chroma_host,
                    "port": self._settings.chroma_port,
                },
            )
            return self._client
        except Exception as exc:
            logger.warning(
                "ChromaDB HTTP client unavailable (%s), falling back to local persistent client",
                exc,
            )

        # Fallback: local persistent client
        try:
            self._client = chromadb.PersistentClient(
                path=self._settings.local_storage_path + "/chroma"
            )
            logger.info("Using local ChromaDB persistent client")
            return self._client
        except Exception as exc:
            raise AppException(
                "Failed to connect to ChromaDB",
                details={
                    "code": "CHROMA_CONNECTION_FAILED",
                    "original_error": str(exc),
                },
            ) from exc

    def _get_collection(self, name: str | None = None) -> Any:
        """Get or create a ChromaDB collection.

        Args:
            name: Collection name override.  Defaults to the configured
                ``chroma_collection``.
        """
        if self._collection is not None and name is None:
            return self._collection

        client = self._get_client()
        collection_name = name or self._settings.chroma_collection

        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise AppException(
                f"Failed to access ChromaDB collection: {collection_name}",
                details={"code": "COLLECTION_ERROR"},
            ) from exc

        if name is None:
            self._collection = collection

        return collection
