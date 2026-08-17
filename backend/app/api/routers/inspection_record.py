"""检查记录路由（API.md §4.1）。保持薄：解析请求、调用 service。"""

import uuid

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile

from app.api.dependencies import CurrentUser, DbSession, get_request_id
from app.schemas.common import Page
from app.schemas.records import (
    GenerateResponse,
    InspectionRecordDetail,
    InspectionRecordListItem,
    InspectionRecordUpdate,
    RecordStatus,
)
from app.services.documents import DOCX_MEDIA_TYPE
from app.services.inspection_record_service import InspectionRecordService

router = APIRouter(prefix="/inspection-record", tags=["inspection-record"])


def _stream(filename: str, data: bytes) -> Response:
    return Response(
        content=data,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate", response_model=GenerateResponse)
def generate(
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
    video: UploadFile = File(...),
    remarks: str | None = Form(None),
) -> GenerateResponse:
    task = InspectionRecordService(session).generate(
        user=current_user,
        filename=video.filename,
        content_type=video.content_type,
        data=video.file.read(),
        remarks=remarks,
        request_id=get_request_id(request),
    )
    return GenerateResponse(task_id=task.id)


@router.get("", response_model=Page[InspectionRecordListItem])
def list_records(
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: RecordStatus | None = None,
) -> Page[InspectionRecordListItem]:
    return InspectionRecordService(session).list(
        current_user, str(status) if status else None, page, page_size
    )


@router.get("/{record_id}", response_model=InspectionRecordDetail)
def get_record(
    record_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> InspectionRecordDetail:
    return InspectionRecordService(session).detail(current_user, record_id)


@router.put("/{record_id}", response_model=InspectionRecordDetail)
def update_record(
    record_id: uuid.UUID,
    payload: InspectionRecordUpdate,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
) -> InspectionRecordDetail:
    return InspectionRecordService(session).update(
        current_user, record_id, payload, request_id=get_request_id(request)
    )


@router.get("/{record_id}/download")
def download_record(
    record_id: uuid.UUID, session: DbSession, current_user: CurrentUser, request: Request
) -> Response:
    filename, data = InspectionRecordService(session).download(
        current_user, record_id, request_id=get_request_id(request)
    )
    return _stream(filename, data)
