"""Inspection record endpoints: generate, retrieve, update, and download."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import FileValidationException, NotFoundException
from app.core.logging import get_logger
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.task import AITask
from app.models.user import User
from app.schemas.inspection import (
    GenerateResponse,
    InspectionRecordResponse,
    InspectionRecordUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["inspection-record"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
TASK_TYPE = "inspection_record_generation"


def _validate_video(file: UploadFile) -> None:
    """Ensure the uploaded file is an allowed video type and within size limits."""
    settings = get_settings()

    if not file.filename:
        raise FileValidationException("Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in ALLOWED_VIDEO_EXTENSIONS:
        allowed_types = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise FileValidationException(
            f"Invalid file type '.{ext}'. Allowed types: {allowed_types}"
        )

    if file.size is not None and file.size > settings.max_upload_size_bytes:
        raise FileValidationException(
            f"File size ({file.size} bytes) exceeds the maximum allowed "
            f"({settings.max_upload_size_bytes} bytes)"
        )


async def _process_inspection_record(task_id: str) -> None:
    """Background task: run the full AI pipeline for inspection record generation.

    This is a placeholder that will be replaced by the actual service
    implementation. The service will:
    1. Extract frames from the video
    2. Run vision analysis on each frame
    3. Run OCR on text regions
    4. Use LLM to reason about findings
    5. Create the InspectionRecord and items
    6. Generate the Word document
    7. Update the task status
    """
    # The service needs its own DB session since this runs in background
    from app.core.database import _get_session_factory
    from app.services.inspection_service import InspectionService

    factory = _get_session_factory()
    async with factory() as db:
        try:
            service = InspectionService(db=db)
            await service.process_generation_task(task_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate an inspection record from video",
)
async def generate(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file (mp4/mov)"),
    remarks: str | None = Form(None, description="Optional remarks for the inspection"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Upload a video and start async inspection record generation.

    The video is validated, stored, and an AI task is created. Processing
    happens in the background; use the returned ``task_id`` to poll status.
    """
    _validate_video(file)

    # Create the AI task record
    task = AITask(
        task_type=TASK_TYPE,
        status="pending",
        progress=0,
        current_stage="uploading",
        input_data={"filename": file.filename, "remarks": remarks},
        created_by=str(current_user.id),
    )
    db.add(task)
    await db.flush()

    logger.info(
        "Inspection record generation task created: %s by user %s",
        task.id,
        current_user.id,
    )

    # Save file and start background processing
    from app.services.storage_service import StorageService

    storage = StorageService()
    await storage.save_upload(file=file, category="video", user_id=str(current_user.id))

    background_tasks.add_task(_process_inspection_record, task.id)

    return GenerateResponse(task_id=task.id)


@router.get(
    "/{record_id}",
    response_model=InspectionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an inspection record by ID",
)
async def get_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InspectionRecordResponse:
    """Return a single inspection record with its items."""
    result = await db.execute(
        select(InspectionRecord)
        .options(selectinload(InspectionRecord.items))
        .where(
            InspectionRecord.id == record_id,
            InspectionRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(f"Inspection record '{record_id}' not found")

    return InspectionRecordResponse.model_validate(record)


@router.put(
    "/{record_id}",
    response_model=InspectionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an inspection record",
)
async def update_record(
    record_id: str,
    body: InspectionRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InspectionRecordResponse:
    """Update fields and/or items of an existing inspection record."""
    result = await db.execute(
        select(InspectionRecord)
        .options(selectinload(InspectionRecord.items))
        .where(
            InspectionRecord.id == record_id,
            InspectionRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(f"Inspection record '{record_id}' not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle items replacement separately
    items_data = update_data.pop("items", None)

    for field, value in update_data.items():
        setattr(record, field, value)

    if items_data is not None:
        # Remove existing items
        for existing_item in list(record.items):
            await db.delete(existing_item)
        await db.flush()

        # Create new items
        for item_schema in items_data:
            item = InspectionRecordItem(
                inspection_record_id=record.id,
                **item_schema
                if isinstance(item_schema, dict)
                else item_schema.model_dump(exclude={"id"}),
            )
            db.add(item)

    await db.flush()

    # Re-fetch to get updated items
    await db.refresh(record)
    result = await db.execute(
        select(InspectionRecord)
        .options(selectinload(InspectionRecord.items))
        .where(InspectionRecord.id == record_id)
    )
    record = result.scalar_one_or_none()

    logger.info("Inspection record %s updated by user %s", record_id, current_user.id)
    return InspectionRecordResponse.model_validate(record)


@router.get(
    "/{record_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download the generated inspection record document",
)
async def download_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Return the generated Word/PDF document for the inspection record."""
    from app.models.document import GeneratedDocument
    from app.models.file import UploadedFile

    # Verify the record exists
    result = await db.execute(
        select(InspectionRecord).where(
            InspectionRecord.id == record_id,
            InspectionRecord.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundException(f"Inspection record '{record_id}' not found")

    # Find the generated document for this record
    doc_result = await db.execute(
        select(GeneratedDocument)
        .join(UploadedFile, GeneratedDocument.uploaded_file_id == UploadedFile.id)
        .where(
            GeneratedDocument.source_entity_type == "inspection_record",
            GeneratedDocument.source_entity_id == record_id,
        )
        .order_by(GeneratedDocument.version.desc())
    )
    generated_doc = doc_result.scalar_one_or_none()
    if generated_doc is None:
        raise NotFoundException("No generated document found for this record")

    # Get the file path from storage
    file_result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == generated_doc.uploaded_file_id)
    )
    uploaded_file = file_result.scalar_one_or_none()
    if uploaded_file is None:
        raise NotFoundException("Document file not found in storage")

    from app.services.storage_service import StorageService

    storage = StorageService()
    file_path = await storage.get_file_path(uploaded_file.storage_path)

    logger.info(
        "Inspection record %s downloaded by user %s",
        record_id,
        current_user.id,
    )

    return FileResponse(
        path=file_path,
        filename=uploaded_file.original_name,
        media_type=uploaded_file.mime_type or "application/octet-stream",
    )
