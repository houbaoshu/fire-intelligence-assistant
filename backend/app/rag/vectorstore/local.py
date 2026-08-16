"""Local vector store: SQLite + numpy cosine search.

A real vector store (not an ANN index) — suitable for development and
small/medium corpora; swap to VECTOR_STORE_PROVIDER=chroma for scale.
Thread-safe: each operation opens its own connection.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

from app.core.config import get_settings

from .base import SearchHit, StoredChunk, VectorStore

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS chunks ("
    " chunk_id TEXT PRIMARY KEY,"
    " document_id TEXT NOT NULL,"
    " text TEXT NOT NULL,"
    " embedding TEXT NOT NULL,"
    " metadata TEXT NOT NULL"
    ")"
)
_INDEX = "CREATE INDEX IF NOT EXISTS ix_chunks_document ON chunks(document_id)"


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class LocalVectorStore(VectorStore):
    name = "local"

    def __init__(self, db_path: Path | None = None):
        settings = get_settings()
        self.db_path = db_path or (settings.data_dir / "vector_store.sqlite")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)
            conn.execute(_INDEX)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # ensure schema on every connection (file may have been recreated)
        conn.execute(_SCHEMA)
        conn.execute(_INDEX)
        conn.commit()
        return conn

    def upsert_chunks(self, chunks: list[StoredChunk]) -> int:
        with self._connect() as conn:
            for c in chunks:
                conn.execute(
                    "INSERT OR REPLACE INTO chunks (chunk_id, document_id, text, embedding, metadata) VALUES (?,?,?,?,?)",
                    (c.chunk_id, c.document_id, c.text, json.dumps(c.embedding), json.dumps(c.metadata)),
                )
            conn.commit()
        return len(chunks)

    def delete_document(self, document_id: str) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.commit()
        return cur.rowcount

    def delete_all(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM chunks")
            conn.commit()
        return cur.rowcount

    def search(self, query_embedding: list[float], top_k: int, *, document_ids: list[str] | None = None) -> list[SearchHit]:
        q = np.asarray(query_embedding, dtype=np.float64)
        sql = "SELECT chunk_id, document_id, text, embedding, metadata FROM chunks"
        params: list = []
        if document_ids is not None:
            if not document_ids:
                return []
            placeholders = ",".join("?" for _ in document_ids)
            sql += f" WHERE document_id IN ({placeholders})"
            params.extend(document_ids)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        scored: list[tuple[float, SearchHit]] = []
        for chunk_id, doc_id, text, emb_json, meta_json in rows:
            emb = np.asarray(json.loads(emb_json), dtype=np.float64)
            score = _cosine(q, emb)
            scored.append(
                (
                    score,
                    SearchHit(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        text=text,
                        metadata=json.loads(meta_json),
                        score=score,
                    ),
                )
            )
        scored.sort(key=lambda t: t[0], reverse=True)
        return [hit for _, hit in scored[:top_k]]

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return int(row[0]) if row else 0

    def count_chunks_for(self, document_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document_id,)).fetchone()
        return int(row[0]) if row else 0
