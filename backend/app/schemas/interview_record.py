"""Interview record schemas (API.md §4.3)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RecordStatus = Literal["draft", "processing", "generated", "reviewed", "finalized", "archived", "failed"]


class InterviewRecordListItem(BaseModel):
    id: str
    title: str | None = None
    interviewee_name: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class InterviewRecordListResponse(BaseModel):
    items: list[InterviewRecordListItem]
    total: int
    page: int
    page_size: int


class InterviewRecordOut(BaseModel):
    id: str
    title: str | None = None
    interviewee_name: str | None = None
    interviewer_names: list[str] | None = None
    location: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript: str | None = None
    structured_content: dict[str, Any] | None = None
    status: str
    source_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class InterviewRecordUpdate(BaseModel):
    title: str | None = None
    interviewee_name: str | None = None
    interviewer_names: list[str] | None = None
    location: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript: str | None = None
    structured_content: dict[str, Any] | None = None
    status: RecordStatus | None = None
