"""Regulation QA schemas (API.md §5)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class QAQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class QASource(BaseModel):
    document_id: str
    title: str
    article: str | None = None
    page: int | None = None
    excerpt: str | None = None
    effective_date: str | None = None
    issuing_authority: str | None = None
    version: str | None = None
    document_type: str | None = None


class QAQueryResponse(BaseModel):
    answer: str
    sources: list[QASource] = []
