from __future__ import annotations

import hashlib
import uuid
from io import BytesIO
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import authorized_user_ids, has_permission, require_permission
from app.db.models import (
    AITask,
    GeneratedDocument,
    InspectionRecord,
    InspectionRecordItem,
    InterviewRecord,
    PhotoReport,
    PhotoReportImage,
    UploadedFile,
    User,
)
from app.db.session import get_db
from app.schemas.business import (
    InspectionItem,
    InspectionRecordResponse,
    InspectionRecordUpdate,
    InterviewRecordResponse,
    InterviewRecordUpdate,
    PhotoImageResponse,
    PhotoReportResponse,
    PhotoReportUpdate,
    TaskCreateResponse,
)
from app.services.audit import add_audit_log
from app.services.documents import inspection_docx, interview_docx, photo_report_docx
from app.services.files import persist_upload
from app.services.storage import StorageProvider
from app.services.tasks import TaskDispatcher, TaskService

router = APIRouter(tags=["records"])
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov"})
AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a"})


def _owned(session: Session, model: type[Any], identifier: uuid.UUID, user: User) -> Any:
    record = session.get(model, identifier)
    if record is None or record.deleted_at is not None:
        raise AppError(status_code=404, code="RECORD_NOT_FOUND", message="Record not found.")
    visible = authorized_user_ids(session, user)
    if visible is not None and record.created_by not in visible:
        raise AppError(status_code=404, code="RECORD_NOT_FOUND", message="Record not found.")
    return record


def _prevent_finalized_change(session: Session, current: str, target: str, user: User) -> None:
    if current == "finalized" and target != "archived":
        raise AppError(
            status_code=409,
            code="FINALIZED_RECORD_IMMUTABLE",
            message="A finalized record cannot be overwritten.",
        )
    if target in {"finalized", "archived"} and not has_permission(
        user, "records.finalize", session
    ):
        raise AppError(
            status_code=403,
            code="FINALIZE_PERMISSION_REQUIRED",
            message="You do not have permission to finalize this record.",
        )


def _existing_task_response(
    session: Session,
    user: User,
    task_type: str,
    idempotency_key: str | None,
) -> TaskCreateResponse | None:
    if not idempotency_key:
        return None
    task = session.scalar(
        select(AITask).where(
            AITask.created_by == user.id,
            AITask.task_type == task_type,
            AITask.idempotency_key == idempotency_key,
            AITask.status.in_(("pending", "queued", "processing", "completed")),
        )
    )
    if task is None:
        return None
    entity_id = (task.result_data or {}).get("entity_id")
    try:
        parsed = uuid.UUID(str(entity_id)) if entity_id else None
    except ValueError:
        parsed = None
    return TaskCreateResponse(task_id=task.id, entity_id=parsed)


def _inspection_response(session: Session, record: InspectionRecord) -> InspectionRecordResponse:
    items = session.scalars(
        select(InspectionRecordItem)
        .where(InspectionRecordItem.inspection_record_id == record.id)
        .order_by(InspectionRecordItem.sort_order)
    ).all()
    return InspectionRecordResponse(
        id=record.id,
        revision=record.revision,
        record_number=record.record_number,
        title=record.title,
        inspection_unit=record.inspection_unit,
        inspection_address=record.inspection_address,
        inspection_date=record.inspection_date,
        inspector_names=record.inspector_names or [],
        contact_person=record.contact_person,
        contact_phone=record.contact_phone,
        source_notes=record.source_notes,
        summary=record.summary,
        conclusion=record.conclusion,
        status=record.status,
        findings=[InspectionItem.model_validate(item) for item in items],
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _photo_response(session: Session, report: PhotoReport) -> PhotoReportResponse:
    images = session.scalars(
        select(PhotoReportImage)
        .where(PhotoReportImage.photo_report_id == report.id)
        .order_by(PhotoReportImage.sort_order)
    ).all()
    return PhotoReportResponse(
        id=report.id,
        revision=report.revision,
        title=report.title,
        inspection_unit=report.inspection_unit,
        inspection_address=report.inspection_address,
        violation_summary=report.violation_summary,
        status=report.status,
        images=[
            PhotoImageResponse(
                id=image.id,
                caption=image.caption,
                detected_address=image.detected_address,
                detected_violation=image.detected_violation,
                is_selected=image.is_selected,
                needs_review=image.needs_review,
                sort_order=image.sort_order,
                frame_timestamp=image.frame_timestamp,
                preview_url=f"/api/photo-report/{report.id}/images/{image.id}",
            )
            for image in images
        ],
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _interview_response(record: InterviewRecord) -> InterviewRecordResponse:
    return InterviewRecordResponse(
        id=record.id,
        revision=record.revision,
        title=record.title,
        interviewee_name=record.interviewee_name,
        interviewer_names=record.interviewer_names or [],
        location=record.location,
        started_at=record.started_at,
        ended_at=record.ended_at,
        transcript=record.transcript,
        structured_content=record.structured_content or {},
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/inspection-record/generate", response_model=TaskCreateResponse, status_code=202)
def generate_inspection_record(
    request: Request,
    video: UploadFile = File(...),
    remarks: str | None = Form(default=None, max_length=10000),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> TaskCreateResponse:
    existing = _existing_task_response(
        session, user, "inspection_record_generation", idempotency_key
    )
    if existing:
        return existing
    settings = request.app.state.settings
    uploaded = persist_upload(
        session,
        cast(StorageProvider, request.app.state.storage),
        video,
        user_id=user.id,
        category="video",
        storage_category="uploads",
        extensions=VIDEO_EXTENSIONS,
        max_bytes=settings.max_video_bytes,
        allowed_mime_prefixes=("video/",),
    )
    record = InspectionRecord(
        status="processing",
        source_file_id=uploaded.id,
        source_notes=remarks,
        created_by=user.id,
    )
    session.add(record)
    session.flush()
    task = TaskService(session).create(
        task_type="inspection_record_generation",
        user_id=user.id,
        input_data={"entity_id": str(record.id), "file_id": str(uploaded.id)},
        result_data={"entity_type": "inspection_record", "entity_id": str(record.id)},
        idempotency_key=idempotency_key,
    )
    record.source_task_id = task.id
    add_audit_log(
        session,
        user_id=user.id,
        action="inspection_record.create",
        entity_type="inspection_record",
        entity_id=record.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    cast(TaskDispatcher, request.app.state.task_dispatcher).submit(task.id)
    return TaskCreateResponse(task_id=task.id, entity_id=record.id)


@router.get("/inspection-record/{record_id}", response_model=InspectionRecordResponse)
def get_inspection_record(
    record_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.read")),
) -> InspectionRecordResponse:
    return _inspection_response(session, _owned(session, InspectionRecord, record_id, user))


@router.put("/inspection-record/{record_id}", response_model=InspectionRecordResponse)
def update_inspection_record(
    record_id: uuid.UUID,
    payload: InspectionRecordUpdate,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> InspectionRecordResponse:
    record: InspectionRecord = _owned(session, InspectionRecord, record_id, user)
    if payload.revision != record.revision:
        raise AppError(
            status_code=409,
            code="REVISION_CONFLICT",
            message="The record changed since it was loaded. Reload before saving.",
        )
    _prevent_finalized_change(session, record.status, payload.status, user)
    for field in (
        "record_number",
        "title",
        "inspection_unit",
        "inspection_address",
        "inspection_date",
        "inspector_names",
        "contact_person",
        "contact_phone",
        "summary",
        "conclusion",
        "status",
    ):
        setattr(record, field, getattr(payload, field))
    record.revision += 1
    session.execute(
        delete(InspectionRecordItem).where(InspectionRecordItem.inspection_record_id == record.id)
    )
    for index, item in enumerate(payload.findings):
        values = item.model_dump(exclude={"id"})
        values["sort_order"] = index
        session.add(InspectionRecordItem(inspection_record_id=record.id, **values))
    add_audit_log(
        session,
        user_id=user.id,
        action="inspection_record.update",
        entity_type="inspection_record",
        entity_id=record.id,
        request_id=getattr(request.state, "request_id", None),
        details={"revision": record.revision, "status": record.status},
    )
    session.commit()
    return _inspection_response(session, record)


@router.get("/inspection-record/{record_id}/download", response_class=FileResponse)
def download_inspection_record(
    record_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("documents.download")),
) -> FileResponse:
    record: InspectionRecord = _owned(session, InspectionRecord, record_id, user)
    items = session.scalars(
        select(InspectionRecordItem).where(InspectionRecordItem.inspection_record_id == record.id)
    ).all()
    content = inspection_docx(record, list(items))
    return _store_document(
        request, session, user, "inspection_record", record.id, record.revision, content
    )


@router.post("/photo-report/generate", response_model=TaskCreateResponse, status_code=202)
def generate_photo_report(
    request: Request,
    video: UploadFile = File(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> TaskCreateResponse:
    existing = _existing_task_response(session, user, "photo_report_generation", idempotency_key)
    if existing:
        return existing
    settings = request.app.state.settings
    uploaded = persist_upload(
        session,
        cast(StorageProvider, request.app.state.storage),
        video,
        user_id=user.id,
        category="video",
        storage_category="uploads",
        extensions=VIDEO_EXTENSIONS,
        max_bytes=settings.max_video_bytes,
        allowed_mime_prefixes=("video/",),
    )
    report = PhotoReport(status="processing", source_file_id=uploaded.id, created_by=user.id)
    session.add(report)
    session.flush()
    task = TaskService(session).create(
        task_type="photo_report_generation",
        user_id=user.id,
        input_data={"entity_id": str(report.id), "file_id": str(uploaded.id)},
        result_data={"entity_type": "photo_report", "entity_id": str(report.id)},
        idempotency_key=idempotency_key,
    )
    report.source_task_id = task.id
    add_audit_log(
        session,
        user_id=user.id,
        action="photo_report.create",
        entity_type="photo_report",
        entity_id=report.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    cast(TaskDispatcher, request.app.state.task_dispatcher).submit(task.id)
    return TaskCreateResponse(task_id=task.id, entity_id=report.id)


@router.get("/photo-report/{report_id}", response_model=PhotoReportResponse)
def get_photo_report(
    report_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.read")),
) -> PhotoReportResponse:
    return _photo_response(session, _owned(session, PhotoReport, report_id, user))


@router.put("/photo-report/{report_id}", response_model=PhotoReportResponse)
def update_photo_report(
    report_id: uuid.UUID,
    payload: PhotoReportUpdate,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> PhotoReportResponse:
    report: PhotoReport = _owned(session, PhotoReport, report_id, user)
    if payload.revision != report.revision:
        raise AppError(status_code=409, code="REVISION_CONFLICT", message="Reload before saving.")
    _prevent_finalized_change(session, report.status, payload.status, user)
    for field in (
        "title",
        "inspection_unit",
        "inspection_address",
        "violation_summary",
        "status",
    ):
        setattr(report, field, getattr(payload, field))
    existing = {
        image.id: image
        for image in session.scalars(
            select(PhotoReportImage).where(PhotoReportImage.photo_report_id == report.id)
        ).all()
    }
    if set(existing) != {image.id for image in payload.images}:
        raise AppError(
            status_code=422,
            code="INVALID_REPORT_IMAGES",
            message="Every report image must be included in the update.",
        )
    for index, incoming in enumerate(sorted(payload.images, key=lambda image: image.sort_order)):
        image = existing[incoming.id]
        for field in (
            "caption",
            "detected_address",
            "detected_violation",
            "is_selected",
            "needs_review",
        ):
            setattr(image, field, getattr(incoming, field))
        image.sort_order = index
    report.revision += 1
    add_audit_log(
        session,
        user_id=user.id,
        action="photo_report.update",
        entity_type="photo_report",
        entity_id=report.id,
        request_id=getattr(request.state, "request_id", None),
        details={"revision": report.revision, "status": report.status},
    )
    session.commit()
    return _photo_response(session, report)


@router.get("/photo-report/{report_id}/images/{image_id}", response_class=FileResponse)
def photo_preview(
    report_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.read")),
) -> FileResponse:
    _owned(session, PhotoReport, report_id, user)
    image = session.get(PhotoReportImage, image_id)
    if image is None or image.photo_report_id != report_id:
        raise AppError(status_code=404, code="IMAGE_NOT_FOUND", message="Image not found.")
    uploaded = session.get(UploadedFile, image.uploaded_file_id)
    if uploaded is None:
        raise AppError(status_code=404, code="IMAGE_NOT_FOUND", message="Image not found.")
    storage = cast(StorageProvider, request.app.state.storage)
    return FileResponse(storage.resolve(uploaded.storage_path), media_type="image/jpeg")


@router.get("/photo-report/{report_id}/download", response_class=FileResponse)
def download_photo_report(
    report_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("documents.download")),
) -> FileResponse:
    report: PhotoReport = _owned(session, PhotoReport, report_id, user)
    images = session.scalars(
        select(PhotoReportImage).where(PhotoReportImage.photo_report_id == report.id)
    ).all()
    if not any(image.is_selected for image in images):
        raise AppError(
            status_code=422,
            code="NO_SELECTED_IMAGES",
            message="Select at least one image before generating the document.",
        )
    file_ids = [image.uploaded_file_id for image in images]
    files = {
        uploaded.id: uploaded
        for uploaded in session.scalars(select(UploadedFile).where(UploadedFile.id.in_(file_ids)))
    }
    content = photo_report_docx(
        report, list(images), files, cast(StorageProvider, request.app.state.storage)
    )
    return _store_document(
        request, session, user, "photo_report", report.id, report.revision, content
    )


@router.post("/interview-record/generate", response_model=TaskCreateResponse, status_code=202)
def generate_interview_record(
    request: Request,
    audio: UploadFile | None = File(default=None),
    video: UploadFile | None = File(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> TaskCreateResponse:
    existing = _existing_task_response(
        session, user, "interview_record_generation", idempotency_key
    )
    if existing:
        return existing
    if (audio is None) == (video is None):
        raise AppError(
            status_code=422,
            code="ONE_MEDIA_FILE_REQUIRED",
            message="Provide exactly one audio or video file.",
        )
    source = audio or video
    assert source is not None
    settings = request.app.state.settings
    is_audio = audio is not None
    uploaded = persist_upload(
        session,
        cast(StorageProvider, request.app.state.storage),
        source,
        user_id=user.id,
        category="audio" if is_audio else "video",
        storage_category="uploads",
        extensions=AUDIO_EXTENSIONS if is_audio else VIDEO_EXTENSIONS,
        max_bytes=settings.max_audio_bytes if is_audio else settings.max_video_bytes,
        allowed_mime_prefixes=("audio/",) if is_audio else ("video/",),
    )
    record = InterviewRecord(status="processing", source_file_id=uploaded.id, created_by=user.id)
    session.add(record)
    session.flush()
    task = TaskService(session).create(
        task_type="interview_record_generation",
        user_id=user.id,
        input_data={"entity_id": str(record.id), "file_id": str(uploaded.id)},
        result_data={"entity_type": "interview_record", "entity_id": str(record.id)},
        idempotency_key=idempotency_key,
    )
    record.source_task_id = task.id
    add_audit_log(
        session,
        user_id=user.id,
        action="interview_record.create",
        entity_type="interview_record",
        entity_id=record.id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.commit()
    cast(TaskDispatcher, request.app.state.task_dispatcher).submit(task.id)
    return TaskCreateResponse(task_id=task.id, entity_id=record.id)


@router.get("/interview-record/{record_id}", response_model=InterviewRecordResponse)
def get_interview_record(
    record_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.read")),
) -> InterviewRecordResponse:
    return _interview_response(_owned(session, InterviewRecord, record_id, user))


@router.put("/interview-record/{record_id}", response_model=InterviewRecordResponse)
def update_interview_record(
    record_id: uuid.UUID,
    payload: InterviewRecordUpdate,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("records.write")),
) -> InterviewRecordResponse:
    record: InterviewRecord = _owned(session, InterviewRecord, record_id, user)
    if payload.revision != record.revision:
        raise AppError(status_code=409, code="REVISION_CONFLICT", message="Reload before saving.")
    _prevent_finalized_change(session, record.status, payload.status, user)
    for field in (
        "title",
        "interviewee_name",
        "interviewer_names",
        "location",
        "started_at",
        "ended_at",
        "structured_content",
        "status",
    ):
        setattr(record, field, getattr(payload, field))
    record.revision += 1
    add_audit_log(
        session,
        user_id=user.id,
        action="interview_record.update",
        entity_type="interview_record",
        entity_id=record.id,
        request_id=getattr(request.state, "request_id", None),
        details={"revision": record.revision, "status": record.status},
    )
    session.commit()
    return _interview_response(record)


@router.get("/interview-record/{record_id}/download", response_class=FileResponse)
def download_interview_record(
    record_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    user: User = Depends(require_permission("documents.download")),
) -> FileResponse:
    record: InterviewRecord = _owned(session, InterviewRecord, record_id, user)
    return _store_document(
        request,
        session,
        user,
        "interview_record",
        record.id,
        record.revision,
        interview_docx(record),
    )


def _store_document(
    request: Request,
    session: Session,
    user: User,
    entity_type: str,
    entity_id: uuid.UUID,
    revision: int,
    content: bytes,
) -> FileResponse:
    storage = cast(StorageProvider, request.app.state.storage)
    latest = session.execute(
        select(GeneratedDocument, UploadedFile)
        .join(UploadedFile, UploadedFile.id == GeneratedDocument.uploaded_file_id)
        .where(
            GeneratedDocument.source_entity_type == entity_type,
            GeneratedDocument.source_entity_id == entity_id,
            GeneratedDocument.source_revision == revision,
        )
        .order_by(GeneratedDocument.version.desc())
    ).first()
    filename = f"{entity_type}-{entity_id}.docx"
    if latest and storage.exists(latest[1].storage_path):
        uploaded = latest[1]
    else:
        stored = storage.save(category="generated", filename=filename, source=BytesIO(content))
        uploaded = UploadedFile(
            original_name=filename,
            storage_path=stored.path,
            storage_provider="local",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_extension=".docx",
            size_bytes=stored.size_bytes,
            checksum=hashlib.sha256(content).hexdigest(),
            category="generated_document",
            uploaded_by=user.id,
        )
        session.add(uploaded)
        session.flush()
        next_version = (
            session.scalar(
                select(func.max(GeneratedDocument.version)).where(
                    GeneratedDocument.source_entity_type == entity_type,
                    GeneratedDocument.source_entity_id == entity_id,
                )
            )
            or 0
        ) + 1
        generated = GeneratedDocument(
            document_type=f"{entity_type}_docx",
            source_entity_type=entity_type,
            source_entity_id=entity_id,
            uploaded_file_id=uploaded.id,
            version=next_version,
            source_revision=revision,
            created_by=user.id,
        )
        session.add(generated)
        add_audit_log(
            session,
            user_id=user.id,
            action="document.generate",
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=getattr(request.state, "request_id", None),
            details={"version": next_version, "revision": revision},
        )
        session.commit()
    return FileResponse(
        storage.resolve(uploaded.storage_path),
        media_type=uploaded.mime_type,
        filename=filename,
    )
