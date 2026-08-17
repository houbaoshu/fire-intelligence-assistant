"""Knowledge Base schema（API.md §6）。"""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from app.models.knowledge import DOCUMENT_STATUSES
from app.schemas.common import UTCModel

DocumentStatus = StrEnum("DocumentStatus", {s.upper(): s for s in DOCUMENT_STATUSES})


class KnowledgeDocumentListItem(UTCModel):
    id: uuid.UUID
    title: str
    document_type: str | None
    status: str
    version: str | None
    issuing_authority: str | None
    effective_date: date | None
    chunk_count: int | None
    created_at: datetime
    updated_at: datetime


class KnowledgeUploadResponse(BaseModel):
    document_id: uuid.UUID
    task_id: uuid.UUID


class KnowledgeDeleteResponse(BaseModel):
    id: uuid.UUID
    deleted: bool


class KnowledgeRebuildResponse(BaseModel):
    task_id: uuid.UUID


class KnowledgeStatusResponse(UTCModel):
    document_count: int
    indexed_count: int
    indexing_count: int
    failed_count: int
    last_indexed_at: datetime | None
