"""Inspection record endpoints (API.md §4.1)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import Response

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ValidationError
from app.schemas.inspection_record import (
    InspectionRecordListItem,
    InspectionRecordListResponse,
    InspectionRecordOut,
    InspectionRecordUpdate,
)
from app.services.inspection_service import InspectionRecordService

router = APIRouter(prefix="/inspection-record", tags=["inspection-record"])


def _item_out(item) -> dict:
    return {
        "id": str(item.id),
        "item_type": item.item_type,
        "location": item.location,
        "description": item.description,
        "legal_basis": item.legal_basis,
        "correction_requirement": item.correction_requirement,
        "severity": item.severity,
        "sort_order": item.sort_order,
    }


def _record_out(record) -> InspectionRecordOut:
    return InspectionRecordOut(
        id=str(record.id),
        record_number=record.record_number,
        title=record.title,
        inspection_unit=record.inspection_unit,
        inspection_address=record.inspection_address,
        inspection_date=record.inspection_date,
        inspector_names=record.inspector_names,
        contact_person=record.contact_person,
        contact_phone=record.contact_phone,
        summary=record.summary,
        conclusion=record.conclusion,
        status=record.status,
        items=[_item_out(i) for i in record.items],
        source_task_id=str(record.source_task_id) if record.source_task_id else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/generate")
def generate(
    user: CurrentUser,
    db: DB,
    video: UploadFile = File(...),
    remarks: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    task_id = InspectionRecordService(db).start_generation(user, video, remarks, idempotency_key=idempotency_key)
    return {"task_id": str(task_id)}


@router.get("", response_model=InspectionRecordListResponse)
def list_records(
    user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
):
    if page_size > 100:
        page_size = 100
    if page < 1:
        raise ValidationError("page 必须 >= 1")
    items, total = InspectionRecordService(db).list(
        user, page=page, page_size=page_size, status=status
    )
    return InspectionRecordListResponse(
        items=[
            InspectionRecordListItem(
                id=str(r.id), record_number=r.record_number, title=r.title,
                inspection_unit=r.inspection_unit, inspection_date=r.inspection_date,
                status=r.status, created_at=r.created_at, updated_at=r.updated_at,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=InspectionRecordOut)
def get_record(user: CurrentUser, db: DB, record_id: uuid.UUID):
    record = InspectionRecordService(db).get(user, record_id)
    return _record_out(record)


@router.put("/{record_id}", response_model=InspectionRecordOut)
def update_record(user: CurrentUser, db: DB, record_id: uuid.UUID, payload: InspectionRecordUpdate):
    record = InspectionRecordService(db).update(user, record_id, payload)
    return _record_out(record)


@router.get("/{record_id}/download")
def download_record(user: CurrentUser, db: DB, record_id: uuid.UUID):
    data, filename = InspectionRecordService(db).download(user, record_id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
