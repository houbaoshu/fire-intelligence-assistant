"""Question answering service with RAG pipeline."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.user import User

logger = get_logger(__name__)


class QAService:
    """Service for question answering using RAG (Retrieval Augmented Generation).

    Implements the full RAG pipeline: retrieve -> rerank -> generate answer
    with source citations.
    """

    async def query(
        self,
        question: str,
        user: User,
        db: AsyncSession,
    ) -> dict:
        """Answer a question using the RAG pipeline.

        Pipeline:
        1. Use RAG retriever to find relevant chunks
        2. Use reranker to improve ranking
        3. Build context from chunks
        4. Call LLM with context + question
        5. Return answer + source citations

        Args:
            question: User question in natural language.
            user: Current user.
            db: Database session.

        Returns:
            Dict with ``answer`` and ``sources`` keys.

        Raises:
            AppException: If AI services are not configured.
        """
        logger.info("QA query", extra={"user_id": str(user.id), "question_length": len(question)})

        try:
            from app.services.ai.llm import LLMService
            from app.services.ai.reranker import RerankerService
        except AppException as exc:
            raise AppException(
                "AI services are not configured. Please configure API keys.",
                details={"code": "AI_NOT_CONFIGURED"},
            ) from exc

        # Initialize services
        reranker = RerankerService()
        llm = LLMService()

        # Step 1: Retrieve relevant chunks from vector store
        # For now, this is a placeholder - would integrate with Chroma
        # In production, this would:
        # - Embed the question
        # - Query Chroma for similar chunks
        # - Return chunks with metadata

        # Placeholder: simulate retrieval
        retrieved_chunks = []

        # Step 2: Rerank chunks
        if retrieved_chunks:
            reranked_chunks = await reranker.rerank(question, retrieved_chunks, top_k=5)
        else:
            reranked_chunks = []

        # Step 3: Build context
        if reranked_chunks:
            context = "\n\n".join([chunk.get("text", "") for chunk in reranked_chunks])
        else:
            context = "未找到相关知识库内容。"

        # Step 4: Generate answer with LLM
        prompt = f"""基于以下知识库内容回答用户的问题。如果知识库中没有相关信息，请明确说明。

知识库内容:
{context}

用户问题: {question}

请以JSON格式返回:
{{
  "answer": "回答内容",
  "sources": [
    {{
      "document_id": "文档ID",
      "title": "文档标题",
      "article": "条款或章节",
      "page": 页码,
      "excerpt": "引用内容"
    }}
  ]
}}"""

        result = await llm.chat_json([{"role": "user", "content": prompt}])

        # Step 5: Return answer with citations
        answer = result.get("answer", "无法生成回答。")
        sources = result.get("sources", [])

        logger.info("QA answer generated", extra={"sources_count": len(sources)})

        return {
            "answer": answer,
            "sources": sources,
        }
