"""查询管线（ARCHITECTURE.md §10.2 / API.md §5）。

`问题 → Retriever → Reranker → 上下文构建 → LLM → 答案+引用`

引用保证机制（specs/regulation-qa.md，禁止编造引用）：
- 检索无候选（或知识库无已索引文档）时直接返回诚实的无依据回答，
  ``sources=[]``，不调用 LLM（AGENTS.md：RAG 启用时禁止凭想象作答）；
- ``sources`` 一律由后端根据实际送入 LLM 上下文的 chunk 元数据构造，
  不解析、不信任 LLM 输出中的任何引用标识；
- Prompt（app/prompts/qa.py）要求模型用 [序号] 引用且禁止虚构，
  序号与 sources 顺序一一对应。
"""

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeDocument
from app.prompts.qa import NO_EVIDENCE_ANSWER, QA_SYSTEM_PROMPT, build_qa_user_prompt
from app.rag.embedding.store import StoredChunk
from app.rag.reranking import Reranker
from app.rag.retrieval import Retriever
from app.services.ai.llm import LLMService

logger = get_logger("rag.query")

_EXCERPT_CHARS = 200


@dataclass
class QAResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    # 诊断信息（供日志区分 reranker 回退；不下发前端）
    reranker_mode: str = "none"


def _context_label(chunk: StoredChunk) -> str:
    meta = chunk.metadata
    parts = [f"《{meta.get('title') or '未命名文档'}》"]
    if meta.get("section"):
        parts.append(str(meta["section"]))
    if meta.get("article_number"):
        parts.append(str(meta["article_number"]))
    if meta.get("page"):
        parts.append(f"第 {meta['page']} 页")
    return " ".join(parts)


def _to_source(chunk: StoredChunk) -> dict:
    meta = chunk.metadata
    excerpt = chunk.content.strip()
    if len(excerpt) > _EXCERPT_CHARS:
        excerpt = excerpt[:_EXCERPT_CHARS] + "…"
    return {
        "document_id": meta.get("document_id"),
        "title": meta.get("title"),
        "article": meta.get("article_number"),
        "page": meta.get("page"),
        "excerpt": excerpt,
        "effective_date": meta.get("effective_date"),
    }


def _indexed_document_count(session: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.deleted_at.is_(None),
            KnowledgeDocument.status == "indexed",
        )
    )
    return session.execute(stmt).scalar_one()


def run_query(
    session: Session,
    question: str,
    *,
    retriever: Retriever | None = None,
    reranker: Reranker | None = None,
    llm: LLMService | None = None,
    settings: Settings | None = None,
) -> QAResult:
    """执行查询管线。AI 失败抛可读 AppException；无证据时返回诚实回答。"""
    s = settings or get_settings()

    # 知识库无已索引文档：不调用任何 AI 服务，直接诚实回答（无法检索即无依据）
    if _indexed_document_count(session) == 0:
        logger.info("知识库无已索引文档，返回无证据回答")
        return QAResult(answer=NO_EVIDENCE_ANSWER, sources=[])

    retriever = retriever or Retriever(session, settings=s)
    candidates = retriever.retrieve(question)
    if not candidates:
        logger.info("检索无候选，返回无证据回答")
        return QAResult(answer=NO_EVIDENCE_ANSWER, sources=[])

    reranker = reranker or Reranker(settings=s)
    ranked, mode = reranker.rerank(question, candidates)
    if not ranked:
        return QAResult(answer=NO_EVIDENCE_ANSWER, sources=[])

    contexts = [f"{_context_label(c)}：{c.content.strip()}" for c in ranked]
    llm = llm or LLMService(s)
    answer = llm.chat(
        [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": build_qa_user_prompt(question, contexts)},
        ]
    )
    # sources 由后端按实际送入上下文的 chunk 元数据构造，与 LLM 输出解耦
    return QAResult(
        answer=answer, sources=[_to_source(c) for c in ranked], reranker_mode=mode
    )
