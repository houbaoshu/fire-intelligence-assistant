"""Knowledge document schema definitions."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentResponse(BaseModel):
    """Response body for a single knowledge document."""

    id: str = Field(..., description="Document UUID")
    title: str = Field(..., description="Document title")
    document_type: str | None = Field(None, description="Source document type")
    status: str = Field(
        ...,
        description="Indexing status: uploaded, parsing, indexing, indexed, failed, outdated",
    )
    version: str | None = Field(None, description="Document version")
    issuing_authority: str | None = Field(None, description="Issuing authority")
    effective_date: date | None = Field(None, description="Date the document takes effect")
    expiration_date: date | None = Field(None, description="Date the document expires")
    chunk_count: int | None = Field(None, ge=0, description="Number of indexed chunks")
    created_by: str = Field(..., description="UUID of the uploading user")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentListResponse(BaseModel):
    """Response body for GET /api/knowledge/documents."""

    documents: list[KnowledgeDocumentResponse] = Field(
        default_factory=list, description="List of knowledge documents"
    )
