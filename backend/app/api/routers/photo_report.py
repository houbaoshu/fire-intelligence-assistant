"""Photo report endpoints (API.md §4.2)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import Response

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ValidationError
from app.schemas.photo_report import (
    PhotoReportListItem,
    PhotoReportListResponse,
    PhotoReportOut,
    PhotoReportUpdate,
)
from app.services.photo_report_service import PhotoReportService

router = APIRouter(prefix="/photo-report", tags=["photo-report"])


def _image_out(img) -> dict:
    return {
        "id": str(img.id),
        "uploaded_file_id": str(img.uploaded_file_id),
        "frame_timestamp": img.frame_timestamp,
        "caption": img.caption,
        "detected_address": img.detected_address,
        "detected_violation": img.detected_violation,
        "is_selected": img.is_selected,
        "sort_order": img.sort_order,
        "created_at": img.created_at,
    }


def _report_out(report) -> PhotoReportOut:
    return PhotoReportOut(
        id=str(report.id),
        title=report.title,
        inspection_unit=report.inspection_unit,
        inspection_address=report.inspection_address,
        violation_summary=report.violation_summary,
        status=report.status,
        images=[_image_out(i) for i in report.images],
        source_task_id=str(report.source_task_id) if report.source_task_id else None,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.post("/generate")
def generate(
    user: CurrentUser,
    db: DB,
    video: UploadFile = File(...),
    remarks: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    task_id = PhotoReportService(db).start_generation(user, video, remarks, idempotency_key=idempotency_key)
    return {"task_id": str(task_id)}


@router.get("", response_model=PhotoReportListResponse)
def list_reports(
    user: CurrentUser,
    db: DB,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
):
    if page_size > 100:
        page_size = 100
    items, total = PhotoReportService(db).list(
        user, page=page, page_size=page_size, status=status
    )
    return PhotoReportListResponse(
        items=[
            PhotoReportListItem(
                id=str(r.id), title=r.title, inspection_unit=r.inspection_unit,
                status=r.status, created_at=r.created_at, updated_at=r.updated_at,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=PhotoReportOut)
def get_report(user: CurrentUser, db: DB, report_id: uuid.UUID):
    return _report_out(PhotoReportService(db).get(user, report_id))


@router.put("/{report_id}", response_model=PhotoReportOut)
def update_report(user: CurrentUser, db: DB, report_id: uuid.UUID, payload: PhotoReportUpdate):
    return _report_out(PhotoReportService(db).update(user, report_id, payload))


@router.get("/{report_id}/download")
def download_report(user: CurrentUser, db: DB, report_id: uuid.UUID):
    data, filename = PhotoReportService(db).download(user, report_id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
