from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.services.ai import OpenAICompatibleClient


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    document: KnowledgeDocument
    score: float


def _terms(text: str) -> set[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9_]{2,}", lowered))
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    words.update(chinese[index : index + 2] for index in range(max(0, len(chinese) - 1)))
    return words


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    return dot / norm if norm else 0.0


class RetrievalService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.client = OpenAICompatibleClient(settings)

    def search(
        self, query: str, limit: int | None = None, creator_ids: set[uuid.UUID] | None = None
    ) -> list[RetrievedChunk]:
        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.knowledge_document_id)
            .where(KnowledgeDocument.status == "indexed", KnowledgeDocument.deleted_at.is_(None))
        )
        if creator_ids is not None:
            statement = statement.where(KnowledgeDocument.created_by.in_(creator_ids))
        rows = self.session.execute(statement).all()
        if not rows:
            return []
        query_embedding: list[float] | None = None
        if self.client.is_configured("embedding") and any(chunk.embedding for chunk, _ in rows):
            query_embedding = self.client.embed([query])[0]
        query_terms = _terms(query)
        ranked: list[RetrievedChunk] = []
        for chunk, document in rows:
            chunk_terms = _terms(chunk.content)
            lexical = len(query_terms & chunk_terms) / max(1, len(query_terms))
            semantic = (
                _cosine(query_embedding, chunk.embedding)
                if query_embedding is not None and chunk.embedding
                else 0.0
            )
            score = semantic * 0.7 + lexical * 0.3 if query_embedding is not None else lexical
            if score > 0:
                ranked.append(RetrievedChunk(chunk=chunk, document=document, score=score))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[: limit or self.settings.retrieval_limit]

    @staticmethod
    def source_reference(item: RetrievedChunk) -> dict[str, object]:
        metadata = item.chunk.chunk_metadata or {}
        excerpt = item.chunk.content[:500]
        return {
            "document_id": item.document.id,
            "title": item.document.title,
            "issuing_authority": item.document.issuing_authority,
            "version": item.document.version,
            "effective_date": item.document.effective_date,
            "article": metadata.get("article") or metadata.get("section"),
            "page": metadata.get("page"),
            "excerpt": excerpt,
            "snippet": excerpt,
        }
