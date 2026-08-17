"""业务记录 schema（API.md §4）：inspection-record / photo-report / interview-record。"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.ai_task import TASK_TYPES
from app.models.inspection import ITEM_TYPES, RECORD_STATUSES, SEVERITIES
from app.schemas.common import UTCModel

RecordStatus = StrEnum("RecordStatus", {s.upper(): s for s in RECORD_STATUSES})
ItemType = StrEnum("ItemType", {s.upper(): s for s in ITEM_TYPES})
Severity = StrEnum("Severity", {s.upper(): s for s in SEVERITIES})
TaskType = StrEnum("TaskType", {t.upper(): t for t in TASK_TYPES})


# ---------- Inspection Record（§4.1） ----------


class InspectionItemInput(BaseModel):
    """items 整体替换语义：无 id=新增；省略已有 id=删除。"""

    id: uuid.UUID | None = None
    item_type: ItemType
    location: str | None = None
    description: str = Field(min_length=1)
    legal_basis: str | None = None
    correction_requirement: str | None = None
    severity: Severity | None = None
    sort_order: int = 0


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
    items: list[InspectionItemInput] | None = None


class InspectionItemResponse(UTCModel):
    id: uuid.UUID
    item_type: str
    location: str | None
    description: str
    legal_basis: str | None
    correction_requirement: str | None
    severity: str | None
    sort_order: int


class InspectionRecordListItem(UTCModel):
    id: uuid.UUID
    record_number: str | None
    title: str | None
    inspection_unit: str | None
    inspection_date: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime


class InspectionRecordDetail(UTCModel):
    id: uuid.UUID
    record_number: str | None
    title: str | None
    inspection_unit: str | None
    inspection_address: str | None
    inspection_date: datetime | None
    inspector_names: list[str] | None
    contact_person: str | None
    contact_phone: str | None
    summary: str | None
    conclusion: str | None
    status: str
    items: list[InspectionItemResponse]
    source_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ---------- Photo Report（§4.2） ----------


class PhotoReportImageInput(BaseModel):
    """按 id 逐项更新；仅 caption / is_selected / sort_order 可改，不涉及增删。"""

    id: uuid.UUID
    caption: str | None = None
    is_selected: bool | None = None
    sort_order: int | None = None


class PhotoReportUpdate(BaseModel):
    title: str | None = None
    inspection_unit: str | None = None
    inspection_address: str | None = None
    violation_summary: str | None = None
    status: RecordStatus | None = None
    images: list[PhotoReportImageInput] | None = None


class PhotoReportListItem(UTCModel):
    id: uuid.UUID
    title: str | None
    inspection_unit: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class PhotoReportImageResponse(UTCModel):
    id: uuid.UUID
    uploaded_file_id: uuid.UUID
    frame_timestamp: float | None
    caption: str | None
    detected_address: str | None
    detected_violation: str | None
    is_selected: bool
    sort_order: int
    created_at: datetime


class PhotoReportDetail(UTCModel):
    id: uuid.UUID
    title: str | None
    inspection_unit: str | None
    inspection_address: str | None
    violation_summary: str | None
    status: str
    images: list[PhotoReportImageResponse]
    source_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ---------- Interview Record（§4.3） ----------


class InterviewRecordUpdate(BaseModel):
    title: str | None = None
    interviewee_name: str | None = None
    interviewer_names: list[str] | None = None
    location: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    transcript: str | None = None
    structured_content: dict | None = None
    status: RecordStatus | None = None


class InterviewRecordListItem(UTCModel):
    id: uuid.UUID
    title: str | None
    interviewee_name: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class InterviewRecordDetail(UTCModel):
    id: uuid.UUID
    title: str | None
    interviewee_name: str | None
    interviewer_names: list[str] | None
    location: str | None
    started_at: datetime | None
    ended_at: datetime | None
    transcript: str | None
    structured_content: dict | None
    status: str
    source_task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ---------- generate 响应 ----------


class GenerateResponse(BaseModel):
    task_id: uuid.UUID
