"""Photo report schemas (API.md §4.2)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RecordStatus = Literal["draft", "processing", "generated", "reviewed", "finalized", "archived", "failed"]


class PhotoReportImageUpdate(BaseModel):
    id: str
    caption: str | None = None
    is_selected: bool | None = None
    sort_order: int | None = None


class PhotoReportImageOut(BaseModel):
    id: str
    uploaded_file_id: str
    frame_timestamp: float | None = None
    caption: str | None = None
    detected_address: str | None = None
    detected_violation: str | None = None
    is_selected: bool
    sort_order: int
    created_at: datetime


class PhotoReportListItem(BaseModel):
    id: str
    title: str | None = None
    inspection_unit: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class PhotoReportListResponse(BaseModel):
    items: list[PhotoReportListItem]
    total: int
    page: int
    page_size: int


class PhotoReportOut(BaseModel):
    id: str
    title: str | None = None
    inspection_unit: str | None = None
    inspection_address: str | None = None
    violation_summary: str | None = None
    status: str
    images: list[PhotoReportImageOut] = []
    source_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PhotoReportUpdate(BaseModel):
    title: str | None = None
    inspection_unit: str | None = None
    inspection_address: str | None = None
    violation_summary: str | None = None
    status: RecordStatus | None = None
    images: list[PhotoReportImageUpdate] | None = None
