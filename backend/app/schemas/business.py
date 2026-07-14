from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


TaskStatus = Literal["pending", "queued", "processing", "completed", "failed", "cancelled"]


class TaskCreateResponse(BaseModel):
    task_id: uuid.UUID
    entity_id: uuid.UUID | None = None


class TaskResponse(ORMModel):
    id: uuid.UUID
    task_type: str
    status: TaskStatus
    progress: int
    current_stage: str | None
    message: str | None = None
    result: dict[str, Any] | None = None
    error_code: str | None
    error_message: str | None
    attempt: int
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


RecordStatus = Literal[
    "draft", "processing", "generated", "reviewed", "finalized", "archived", "failed"
]


class InspectionItem(BaseModel):
    id: uuid.UUID | None = None
    item_type: Literal["compliant", "violation", "hazard", "observation", "recommendation"]
    location: str | None = Field(default=None, max_length=300)
    description: str = Field(min_length=1, max_length=8000)
    legal_basis: str | None = Field(default=None, max_length=8000)
    correction_requirement: str | None = Field(default=None, max_length=8000)
    severity: Literal["low", "medium", "high", "critical"] | None = None
    sort_order: int = Field(default=0, ge=0)


class InspectionRecordUpdate(BaseModel):
    revision: int = Field(ge=1)
    record_number: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=300)
    inspection_unit: str | None = Field(default=None, max_length=300)
    inspection_address: str | None = Field(default=None, max_length=500)
    inspection_date: datetime | None = None
    inspector_names: list[str] = Field(default_factory=list, max_length=20)
    contact_person: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=100)
    source_notes: str | None = Field(default=None, max_length=10000)
    summary: str | None = Field(default=None, max_length=20000)
    conclusion: str | None = Field(default=None, max_length=20000)
    status: RecordStatus = "draft"
    findings: list[InspectionItem] = Field(default_factory=list, max_length=500)


class InspectionRecordResponse(InspectionRecordUpdate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PhotoImageUpdate(BaseModel):
    id: uuid.UUID
    caption: str | None = Field(default=None, max_length=2000)
    detected_address: str | None = Field(default=None, max_length=500)
    detected_violation: str | None = Field(default=None, max_length=4000)
    is_selected: bool = True
    needs_review: bool = True
    sort_order: int = Field(default=0, ge=0)


class PhotoImageResponse(PhotoImageUpdate):
    frame_timestamp: float | None = None
    preview_url: str


class PhotoReportUpdate(BaseModel):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=300)
    inspection_unit: str | None = Field(default=None, max_length=300)
    inspection_address: str | None = Field(default=None, max_length=500)
    violation_summary: str | None = Field(default=None, max_length=10000)
    status: RecordStatus = "draft"
    images: list[PhotoImageUpdate] = Field(default_factory=list, max_length=100)


class PhotoReportResponse(BaseModel):
    id: uuid.UUID
    revision: int
    title: str | None
    inspection_unit: str | None
    inspection_address: str | None
    violation_summary: str | None
    status: RecordStatus
    images: list[PhotoImageResponse]
    created_at: datetime
    updated_at: datetime


class InterviewRecordUpdate(BaseModel):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=300)
    interviewee_name: str | None = Field(default=None, max_length=100)
    interviewer_names: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = Field(default=None, max_length=500)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    structured_content: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = "draft"

    @model_validator(mode="after")
    def validate_time_range(self) -> InterviewRecordUpdate:
        if self.started_at and self.ended_at and self.started_at > self.ended_at:
            raise ValueError("started_at must not be after ended_at")
        return self


class InterviewRecordResponse(InterviewRecordUpdate):
    id: uuid.UUID
    transcript: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentResponse(ORMModel):
    id: uuid.UUID
    title: str
    name: str
    document_type: str | None
    status: str
    version: str | None
    issuing_authority: str | None
    effective_date: date | None
    expiration_date: date | None
    chunk_count: int | None
    error: str | None
    task_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeUploadResponse(BaseModel):
    document: KnowledgeDocumentResponse
    task_id: uuid.UUID


class QASource(BaseModel):
    document_id: uuid.UUID
    title: str
    issuing_authority: str | None = None
    version: str | None = None
    effective_date: date | None = None
    article: str | None = None
    page: int | None = None
    excerpt: str
    snippet: str


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class QAResponse(BaseModel):
    answer: str
    sources: list[QASource]
    evidence_status: Literal["grounded", "no_evidence", "retrieval_only"]


class Metric(BaseModel):
    id: str
    label: str
    value: int | float | None
    unit: str
    available: bool = True


class StatisticsResponse(BaseModel):
    scope: Literal["personal", "organization", "system"]
    period_start: datetime | None
    period_end: datetime
    timezone: str
    last_updated_at: datetime
    metrics: list[Metric]
    task_statuses: dict[str, int]
    knowledge_statuses: dict[str, int]


class NamePayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OrganizationCreate(NamePayload):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$")


class DepartmentCreate(NamePayload):
    organization_id: uuid.UUID
    parent_id: uuid.UUID | None = None


class MembershipCreate(BaseModel):
    organization_id: uuid.UUID
    department_id: uuid.UUID | None = None
    user_id: uuid.UUID
    title: str | None = Field(default=None, max_length=100)


class PlatformResourceCreate(BaseModel):
    data: dict[str, Any]
