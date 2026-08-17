"""Retriever：问题 → Embedding → 向量库 top-k 候选。

权限/状态过滤在内容送入 AI 模型之前完成（specs/regulation-qa.md）：
只有 ``indexed`` 且未软删除的知识文档可被检索到；已删除文档即使向量
库残留也不会进入候选。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.knowledge import KnowledgeDocument
from app.rag.embedding.store import StoredChunk, VectorStore, get_vector_store
from app.services.ai.embedding import EmbeddingService

# 过滤后候选不足时的超额检索倍数
_OVERFETCH = 3


class Retriever:
    def __init__(
        self,
        session: Session,
        embedding: EmbeddingService | None = None,
        store: VectorStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._embedding = embedding or EmbeddingService(self._settings)
        self._store = store or get_vector_store(self._settings)

    def retrieve(self, question: str, top_k: int | None = None) -> list[StoredChunk]:
        k = top_k or self._settings.RAG_RETRIEVAL_TOP_K
        vector = self._embedding.embed([question])[0]
        candidates = self._store.search(vector, k * _OVERFETCH)
        allowed = self._indexed_document_ids()
        return [c for c in candidates if c.document_id in allowed][:k]

    def _indexed_document_ids(self) -> set[str]:
        stmt = select(KnowledgeDocument.id).where(
            KnowledgeDocument.deleted_at.is_(None),
            KnowledgeDocument.status == "indexed",
        )
        return {str(row) for row in self._session.execute(stmt).scalars().all()}
