"""Interview record endpoints (API.md §4.3)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import Response

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ValidationError
from app.schemas.interview_record import (
    InterviewRecordListItem,
    InterviewRecordListResponse,
    InterviewRecordOut,
    InterviewRecordUpdate,
)
from app.services.interview_service import InterviewRecordService

router = APIRouter(prefix="/interview-record", tags=["interview-record"])


def _record_out(record) -> InterviewRecordOut:
    return InterviewRecordOut(
        id=str(record.id),
        title=record.title,
        interviewee_name=record.interviewee_name,
        interviewer_names=record.interviewer_names,
        location=record.location,
        started_at=record.started_at,
        ended_at=record.ended_at,
        transcript=record.transcript,
        structured_content=record.structured_content,
        status=record.status,
        source_task_id=str(record.source_task_id) if record.source_task_id else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/generate")
def generate(
    user: CurrentUser,
    db: DB,
    audio: UploadFile = File(...),
    remarks: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # v1: audio source only — reject video fields explicitly
    task_id = InterviewRecordService(db).start_generation(user, audio, remarks, idempotency_key=idempotency_key)
    return {"task_id": str(task_id)}


@router.get("", response_model=InterviewRecordListResponse)
def list_records(
    user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
):
    if page_size > 100:
        page_size = 100
    items, total = InterviewRecordService(db).list(
        user, page=page, page_size=page_size, status=status
    )
    return InterviewRecordListResponse(
        items=[
            InterviewRecordListItem(
                id=str(r.id), title=r.title, interviewee_name=r.interviewee_name,
                status=r.status, created_at=r.created_at, updated_at=r.updated_at,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=InterviewRecordOut)
def get_record(user: CurrentUser, db: DB, record_id: uuid.UUID):
    return _record_out(InterviewRecordService(db).get(user, record_id))


@router.put("/{record_id}", response_model=InterviewRecordOut)
def update_record(user: CurrentUser, db: DB, record_id: uuid.UUID, payload: InterviewRecordUpdate):
    return _record_out(InterviewRecordService(db).update(user, record_id, payload))


@router.get("/{record_id}/download")
def download_record(user: CurrentUser, db: DB, record_id: uuid.UUID):
    data, filename = InterviewRecordService(db).download(user, record_id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
