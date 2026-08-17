"""Embedding 索引步骤：向量存储抽象与实现（ARCHITECTURE.md §4.4 / §10.1）。

向量库只存检索数据（chunk 向量、chunk 元数据、来源引用），不当业务库；
业务事实源始终在关系数据库（knowledge_documents）。

- 默认实现 ``LocalVectorStore``：SQLite 文件 + numpy 余弦检索，存
  ``VECTOR_STORE_DIR``，零额外服务依赖。
- ``ChromaVectorStore`` 为可选 provider（``VECTOR_STORE_PROVIDER=chroma``），
  未安装 chromadb 时报可读错误。
"""

from app.rag.embedding.store import (
    ChunkRecord,
    StoredChunk,
    VectorStore,
    get_vector_store,
    reset_vector_store,
)

__all__ = [
    "ChunkRecord",
    "StoredChunk",
    "VectorStore",
    "get_vector_store",
    "reset_vector_store",
]
