"""Inspection record schemas (API.md §4.1)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RecordStatus = Literal["draft", "processing", "generated", "reviewed", "finalized", "archived", "failed"]
ItemType = Literal["compliant", "violation", "hazard", "observation", "recommendation"]
Severity = Literal["low", "medium", "high", "critical"]


class InspectionRecordItemIn(BaseModel):
    id: str | None = None
    item_type: ItemType
    location: str | None = None
    description: str = Field(min_length=1)
    legal_basis: str | None = None
    correction_requirement: str | None = None
    severity: Severity | None = None
    sort_order: int = 0


class InspectionRecordItemOut(BaseModel):
    id: str
    item_type: str
    location: str | None = None
    description: str
    legal_basis: str | None = None
    correction_requirement: str | None = None
    severity: str | None = None
    sort_order: int


class InspectionRecordListItem(BaseModel):
    id: str
    record_number: str | None = None
    title: str | None = None
    inspection_unit: str | None = None
    inspection_date: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class InspectionRecordListResponse(BaseModel):
    items: list[InspectionRecordListItem]
    total: int
    page: int
    page_size: int


class InspectionRecordOut(BaseModel):
    id: str
    record_number: str | None = None
    title: str | None = None
    inspection_unit: str | None = None
    inspection_address: str | None = None
    inspection_date: datetime | None = None
    inspector_names: list[str] | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    summary: str | None = None
    conclusion: str | None = None
    status: str
    items: list[InspectionRecordItemOut] = []
    source_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class InspectionRecordUpdate(BaseModel):
    title: str | None = None
    inspection_unit: str | None = None
    inspection_address: str | None = None
    inspection_date: datetime | None = None
    inspector_names: list[str] | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    summary: str | None = None
    conclusion: str | None = None
    status: RecordStatus | None = None
    items: list[InspectionRecordItemIn] | None = None
