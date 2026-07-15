"""Fire regulation QA schema definitions."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class QAQueryRequest(BaseModel):
    """Request body for POST /api/qa/query."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Fire regulation question in natural language",
    )


class QASource(BaseModel):
    """A single source citation returned with a QA answer."""

    document_id: str | None = Field(None, description="Source document UUID")
    title: str | None = Field(None, description="Source document title")
    article: str | None = Field(None, description="Article or section reference")
    page: int | None = Field(None, ge=1, description="Page number in the source document")
    excerpt: str | None = Field(None, description="Quoted or matched excerpt")
    effective_date: date | None = Field(None, description="Effective date of the source document")


class QAResponse(BaseModel):
    """Response body for POST /api/qa/query."""

    answer: str = Field(..., description="Grounded answer text")
    sources: list[QASource] = Field(
        default_factory=list, description="Source citations supporting the answer"
    )
