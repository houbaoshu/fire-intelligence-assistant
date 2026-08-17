"""向量存储抽象与实现。模块职责见 app/rag/embedding/__init__.py。"""

import json
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException


def vector_store_error(message: str) -> AppException:
    return AppException("VECTOR_STORE_ERROR", message, 500)


@dataclass
class ChunkRecord:
    """写入向量库的一条 chunk（派生检索数据，非业务记录）。"""

    chunk_index: int
    content: str
    metadata: dict
    vector: list[float]


@dataclass
class StoredChunk:
    """检索命中项。score 为余弦相似度（越大越相关）。"""

    chunk_id: str
    document_id: str
    content: str
    metadata: dict
    score: float


class VectorStore(ABC):
    @abstractmethod
    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> None:
        """整体替换某文档的全部 chunk（先删后写，一次完成）。

        调用方必须先完成解析/切分/embedding 再调用本方法，保证失败时
        不会破坏该文档最后可用的索引（specs/knowledge-base.md 重建规则）。
        """

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        """移除某文档的全部 chunk。"""

    @abstractmethod
    def search(self, vector: list[float], top_k: int) -> list[StoredChunk]:
        """余弦相似度检索，按分数降序返回至多 top_k 条。"""

    @abstractmethod
    def list_document_ids(self) -> list[str]:
        """当前有索引数据的文档 ID 列表（重建时用于清理游离 chunk）。"""

    @abstractmethod
    def count(self) -> int:
        """chunk 总数（诊断用）。"""


class LocalVectorStore(VectorStore):
    """SQLite 文件 + numpy 余弦检索（开发态默认，零额外服务依赖）。"""

    def __init__(self, dir_path: str | Path) -> None:
        base = Path(dir_path)
        base.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(base / "vectors.db", check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_chunks_document ON chunks(document_id)"
            )
            self._conn.commit()

    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "DELETE FROM chunks WHERE document_id = ?", (document_id,)
                )
                self._conn.executemany(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (
                            uuid.uuid4().hex,
                            document_id,
                            r.chunk_index,
                            r.content,
                            json.dumps(r.metadata, ensure_ascii=False),
                            np.asarray(r.vector, dtype=np.float32).tobytes(),
                        )
                        for r in records
                    ],
                )

    def delete_document(self, document_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

    def search(self, vector: list[float], top_k: int) -> list[StoredChunk]:
        query = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(query))
        if norm == 0.0:
            raise vector_store_error("查询向量为零向量，无法检索")
        query = query / norm
        with self._lock:
            rows = self._conn.execute(
                "SELECT chunk_id, document_id, content, metadata, embedding FROM chunks"
            ).fetchall()
        if not rows:
            return []
        matrix = np.frombuffer(b"".join(r[4] for r in rows), dtype=np.float32).reshape(
            len(rows), -1
        )
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0.0] = 1.0
        scores = (matrix / norms[:, None]) @ query
        order = np.argsort(scores)[::-1][:top_k]
        return [
            StoredChunk(
                chunk_id=rows[i][0],
                document_id=rows[i][1],
                content=rows[i][2],
                metadata=json.loads(rows[i][3]),
                score=float(scores[i]),
            )
            for i in order
        ]

    def list_document_ids(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute("SELECT DISTINCT document_id FROM chunks").fetchall()
        return [r[0] for r in rows]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


class ChromaVectorStore(VectorStore):
    """可选 provider：Chroma 持久库（需安装 chromadb，同一 collection 存全部 chunk）。"""

    def __init__(self, dir_path: str | Path) -> None:
        try:
            import chromadb
        except ImportError:
            raise vector_store_error(
                "向量库 provider 配置为 chroma 但未安装 chromadb，"
                "请安装依赖或将 VECTOR_STORE_PROVIDER 改为 local"
            )
        base = Path(dir_path)
        base.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(base / "chroma"))
        self._collection = client.get_or_create_collection(
            "knowledge_chunks", metadata={"hnsw:space": "cosine"}
        )

    @staticmethod
    def _clean_metadata(metadata: dict) -> dict:
        # Chroma 元数据值仅支持 str/int/float/bool，None 统一转为空串
        return {k: ("" if v is None else v) for k, v in metadata.items()}

    def replace_document(self, document_id: str, records: list[ChunkRecord]) -> None:
        self.delete_document(document_id)
        if not records:
            return
        self._collection.add(
            ids=[uuid.uuid4().hex for _ in records],
            embeddings=[r.vector for r in records],
            documents=[r.content for r in records],
            metadatas=[
                {**self._clean_metadata(r.metadata), "document_id": document_id}
                for r in records
            ],
        )

    def delete_document(self, document_id: str) -> None:
        existing = self._collection.get(where={"document_id": document_id})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def search(self, vector: list[float], top_k: int) -> list[StoredChunk]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[vector], n_results=min(top_k, self._collection.count())
        )
        chunks = []
        for i, chunk_id in enumerate(result["ids"][0]):
            metadata = result["metadatas"][0][i] or {}
            distance = result["distances"][0][i]
            chunks.append(
                StoredChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata.get("document_id", "")),
                    content=result["documents"][0][i] or "",
                    metadata=metadata,
                    score=1.0 - float(distance),
                )
            )
        return chunks

    def list_document_ids(self) -> list[str]:
        metadatas = self._collection.get()["metadatas"]
        return sorted({str(m.get("document_id", "")) for m in metadatas if m})

    def count(self) -> int:
        return self._collection.count()


_store: VectorStore | None = None
_store_lock = threading.Lock()


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    """进程级单例（配置来自 get_settings()；测试可用 reset_vector_store 重置）。"""
    global _store
    with _store_lock:
        if _store is None:
            s = settings or get_settings()
            if s.VECTOR_STORE_PROVIDER == "local":
                _store = LocalVectorStore(s.VECTOR_STORE_DIR)
            elif s.VECTOR_STORE_PROVIDER == "chroma":
                _store = ChromaVectorStore(s.VECTOR_STORE_DIR)
            else:
                raise vector_store_error(
                    f"不支持的向量库 provider: {s.VECTOR_STORE_PROVIDER}"
                )
        return _store


def reset_vector_store() -> None:
    global _store
    with _store_lock:
        _store = None
