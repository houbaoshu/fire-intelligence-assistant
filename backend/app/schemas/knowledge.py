"""Knowledge base schemas (API.md §6)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class KnowledgeDocumentListItem(BaseModel):
    id: str
    title: str
    document_type: str | None = None
    status: str
    version: str | None = None
    issuing_authority: str | None = None
    effective_date: date | None = None
    chunk_count: int | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentListItem]
    total: int
    page: int
    page_size: int


class KnowledgeUploadResponse(BaseModel):
    document_id: str
    task_id: str


class KnowledgeDeleteResponse(BaseModel):
    id: str
    deleted: bool


class KnowledgeRebuildResponse(BaseModel):
    task_id: str


class KnowledgeStatusResponse(BaseModel):
    document_count: int
    indexed_count: int
    indexing_count: int
    failed_count: int
    last_indexed_at: datetime | None = None
