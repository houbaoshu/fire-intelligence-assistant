"""Reranker：在上下文送入 LLM 之前提升检索质量。

- 配置了 reranker provider（AI_RERANKER_*）时调用远端 rerank API；
  provider 调用失败按可读错误处理，不静默降级（AI_CONTEXT.md Error Handling）。
- 未配置时提供确定性本地回退：按检索分数降序透传，并在日志与返回值中
  明确标记 ``passthrough``，调用方与排障时可区分。
"""

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.rag.embedding.store import StoredChunk
from app.services.ai.reranker import RerankerService

logger = get_logger("rag.reranking")


class Reranker:
    def __init__(
        self,
        service: RerankerService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._service = service or RerankerService(self._settings)

    def rerank(
        self, query: str, chunks: list[StoredChunk], top_n: int | None = None
    ) -> tuple[list[StoredChunk], str]:
        """返回 (重排后 chunks, 模式)；模式为 ``provider`` / ``passthrough``。"""
        n = top_n or self._settings.RAG_CONTEXT_TOP_N
        if not chunks:
            return [], "passthrough"
        if not self._service.is_available:
            logger.info("reranker 未配置，按检索分数透传（passthrough）")
            return sorted(chunks, key=lambda c: c.score, reverse=True)[:n], "passthrough"
        ranked = self._service.rerank(query, [c.content for c in chunks], top_n=n)
        return [chunks[i] for i, _ in ranked], "provider"
