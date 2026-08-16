"""Regulation QA service.

Pipeline: query -> permission-scoped retrieval -> (optional rerank) ->
context building -> LLM answer -> citations (specs/regulation-qa.md).
Retrieval is mandatory; answers are grounded in retrieved chunks.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.prompts.qa import QA_SYSTEM, build_qa_user_prompt
from app.rag.retrieval import RetrievalService
from app.services.ai.llm import LLMService
from app.services.knowledge_service import KnowledgeBaseService

logger = get_logger("qa")

NO_EVIDENCE_MESSAGE = "知识库中未检索到与该问题直接相关的法规材料,无法给出有依据的回答。请补充相关法规文档后再试。"


class QAService:
    def __init__(self, db: Session):
        self.db = db
        self.retrieval = RetrievalService()
        self.llm = LLMService()

    def query(self, user, question: str) -> dict:
        # 1. permission-scoped retrieval (mandatory)
        document_ids = KnowledgeBaseService(self.db).accessible_document_ids(user)
        hits = self.retrieval.search(question, document_ids=document_ids)

        sources = []
        for hit in hits:
            meta = hit.metadata
            sources.append(
                {
                    "document_id": meta.get("document_id") or hit.document_id,
                    "title": meta.get("title", ""),
                    "article": meta.get("article"),
                    "page": meta.get("page"),
                    "excerpt": hit.text[:200],
                    "effective_date": str(meta.get("effective_date")) if meta.get("effective_date") else None,
                    "issuing_authority": meta.get("issuing_authority"),
                    "version": meta.get("version"),
                    "document_type": meta.get("document_type"),
                }
            )

        if not hits:
            # honest no-evidence result, never a fabricated answer
            return {"answer": NO_EVIDENCE_MESSAGE, "sources": []}

        context = "\n\n".join(
            f"[{i + 1}] (文档:{h.metadata.get('title', '')}"
            + (f",{h.metadata.get('article', '')}" if h.metadata.get("article") else "")
            + f") {h.text}"
            for i, h in enumerate(hits)
        )

        # 2. LLM answer grounded in context (prompt resolved via catalog)
        from app.services.aiplatform.plugin_service import get_registry
        from app.services.aiplatform.prompt_service import PromptService

        try:
            system = PromptService(self.db).get_active("qa.QA_SYSTEM")
        except Exception:
            system = QA_SYSTEM
        answer = self.llm.chat(
            system,
            build_qa_user_prompt(question, context),
            temperature=0.2,
        )
        result = {"answer": answer, "sources": sources}
        # 3. plugin post-processing hooks
        result = get_registry().run_hook("qa_post_process", result)
        return result
