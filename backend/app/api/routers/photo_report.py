"""拍照报告路由（API.md §4.2）。保持薄：解析请求、调用 service。"""

import uuid

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, Response, UploadFile

from app.api.dependencies import (
    CurrentUser,
    DbSession,
    get_request_id,
    require_permission,
)
from app.models.user import User
from app.schemas.common import Page
from app.schemas.records import (
    GenerateResponse,
    PhotoReportDetail,
    PhotoReportListItem,
    PhotoReportUpdate,
    RecordStatus,
)
from app.services.documents import DOCX_MEDIA_TYPE
from app.services.photo_report_service import PhotoReportService

router = APIRouter(prefix="/photo-report", tags=["photo-report"])


def _stream(filename: str, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate", response_model=GenerateResponse)
def generate(
    session: DbSession,
    request: Request,
    current_user: User = Depends(require_permission("record.create")),
    video: UploadFile = File(...),
    remarks: str | None = Form(None),
    idempotency_key: str | None = Header(None),
) -> GenerateResponse:
    task = PhotoReportService(session).generate(
        user=current_user,
        filename=video.filename,
        content_type=video.content_type,
        data=video.file.read(),
        remarks=remarks,
        request_id=get_request_id(request),
        idempotency_key=idempotency_key,
    )
    return GenerateResponse(task_id=task.id)


@router.get("", response_model=Page[PhotoReportListItem])
def list_reports(
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: RecordStatus | None = None,
) -> Page[PhotoReportListItem]:
    return PhotoReportService(session).list(
        current_user, str(status) if status else None, page, page_size
    )


@router.get("/{report_id}", response_model=PhotoReportDetail)
def get_report(
    report_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> PhotoReportDetail:
    return PhotoReportService(session).detail(current_user, report_id)


@router.put("/{report_id}", response_model=PhotoReportDetail)
def update_report(
    report_id: uuid.UUID,
    payload: PhotoReportUpdate,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
) -> PhotoReportDetail:
    return PhotoReportService(session).update(
        current_user, report_id, payload, request_id=get_request_id(request)
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID, session: DbSession, current_user: CurrentUser, request: Request
) -> Response:
    filename, data = PhotoReportService(session).download(
        current_user, report_id, request_id=get_request_id(request)
    )
    return _stream(filename, data)
