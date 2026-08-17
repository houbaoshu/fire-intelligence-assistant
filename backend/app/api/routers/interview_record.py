"""询问记录路由（API.md §4.3）。保持薄：解析请求、调用 service。"""

import uuid

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile

from app.api.dependencies import CurrentUser, DbSession, get_request_id
from app.schemas.common import Page
from app.schemas.records import (
    GenerateResponse,
    InterviewRecordDetail,
    InterviewRecordListItem,
    InterviewRecordUpdate,
    RecordStatus,
)
from app.services.documents import DOCX_MEDIA_TYPE
from app.services.interview_record_service import InterviewRecordService

router = APIRouter(prefix="/interview-record", tags=["interview-record"])


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
    audio: UploadFile = File(...),
    remarks: str | None = Form(None),
) -> GenerateResponse:
    task = InterviewRecordService(session).generate(
        user=current_user,
        filename=audio.filename,
        content_type=audio.content_type,
        data=audio.file.read(),
        remarks=remarks,
        request_id=get_request_id(request),
    )
    return GenerateResponse(task_id=task.id)


@router.get("", response_model=Page[InterviewRecordListItem])
def list_records(
    session: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: RecordStatus | None = None,
) -> Page[InterviewRecordListItem]:
    return InterviewRecordService(session).list(
        current_user, str(status) if status else None, page, page_size
    )


@router.get("/{record_id}", response_model=InterviewRecordDetail)
def get_record(
    record_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> InterviewRecordDetail:
    return InterviewRecordService(session).detail(current_user, record_id)


@router.put("/{record_id}", response_model=InterviewRecordDetail)
def update_record(
    record_id: uuid.UUID,
    payload: InterviewRecordUpdate,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
) -> InterviewRecordDetail:
    return InterviewRecordService(session).update(
        current_user, record_id, payload, request_id=get_request_id(request)
    )


@router.get("/{record_id}/download")
def download_record(
    record_id: uuid.UUID, session: DbSession, current_user: CurrentUser, request: Request
) -> Response:
    filename, data = InterviewRecordService(session).download(
        current_user, record_id, request_id=get_request_id(request)
    )
    return _stream(filename, data)
