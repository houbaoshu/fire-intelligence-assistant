"""Chroma vector store adapter (optional; requires chromadb installed).

Enable with VECTOR_STORE_PROVIDER=chroma.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import AIProviderError

from .base import SearchHit, StoredChunk, VectorStore


class ChromaVectorStore(VectorStore):
    name = "chroma"

    def __init__(self, collection_name: str = "fire_knowledge"):
        try:
            import chromadb  # type: ignore  # noqa: PLC0415
        except ImportError:
            raise AIProviderError("未安装 chromadb,请安装后启用 Chroma 向量库") from None
        self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(self, chunks: list[StoredChunk]) -> int:
        ids = [c.chunk_id or str(uuid.uuid4()) for c in chunks]
        docs = [c.text for c in chunks]
        embeddings = [c.embedding for c in chunks]
        metadatas: list[dict[str, Any]] = []
        for c in chunks:
            meta = dict(c.metadata)
            meta["document_id"] = c.document_id
            metadatas.append(meta)
        self._collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
        return len(chunks)

    def delete_document(self, document_id: str) -> int:
        existing = self._collection.get(where={"document_id": document_id})
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def delete_all(self) -> int:
        count = self._collection.count()
        self._collection.delete()
        self._collection = self._client.create_collection(name=self._collection.name, metadata={"hnsw:space": "cosine"})
        return count

    def search(self, query_embedding: list[float], top_k: int, *, document_ids: list[str] | None = None) -> list[SearchHit]:
        where: dict | None = None
        if document_ids is not None:
            if not document_ids:
                return []
            where = {"document_id": {"$in": document_ids}}
        res = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[SearchHit] = []
        ids = res.get("ids") or [[]]
        docs = res.get("documents") or [[]]
        metas = res.get("metadatas") or [[]]
        dists = res.get("distances") or [[]]
        for i, cid in enumerate(ids[0]):
            meta = dict(metas[0][i] or {})
            doc_id = meta.pop("document_id", "")
            score = 1.0 - float(dists[0][i])
            hits.append(SearchHit(chunk_id=cid, document_id=doc_id, text=docs[0][i], metadata=meta, score=score))
        return hits

    def count_chunks(self) -> int:
        return self._collection.count()

    def count_chunks_for(self, document_id: str) -> int:
        return len(self._collection.get(where={"document_id": document_id}).get("ids") or [])
