"""Interview record endpoints: generate, retrieve, update, and download."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import FileValidationException, NotFoundException
from app.core.logging import get_logger
from app.models.interview import InterviewRecord
from app.models.task import AITask
from app.models.user import User
from app.schemas.inspection import GenerateResponse
from app.schemas.interview import InterviewRecordResponse, InterviewRecordUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["interview-record"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
TASK_TYPE = "interview_record_generation"


def _validate_media(file: UploadFile) -> None:
    """Ensure the uploaded file is an allowed audio/video type and within size limits."""
    settings = get_settings()

    if not file.filename:
        raise FileValidationException("Filename is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise FileValidationException(
            f"Invalid file type '.{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if file.size is not None and file.size > settings.max_upload_size_bytes:
        raise FileValidationException(
            f"File size ({file.size} bytes) exceeds the maximum allowed "
            f"({settings.max_upload_size_bytes} bytes)"
        )


async def _process_interview_record(task_id: str) -> None:
    """Background task: run the full AI pipeline for interview record generation.

    This is a placeholder that will be replaced by the actual service
    implementation. The service will:
    1. Transcribe the audio/video using speech-to-text
    2. Use LLM to structure the interview content
    3. Create the InterviewRecord
    4. Generate the Word document
    5. Update the task status
    """
    from app.core.database import _get_session_factory
    from app.services.interview_service import InterviewService

    factory = _get_session_factory()
    async with factory() as db:
        try:
            service = InterviewService(db=db)
            await service.process_generation_task(task_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate an interview record from audio or video",
)
async def generate(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio or video file"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Upload an audio/video file and start async interview record generation.

    The file is validated, stored, and an AI task is created. Processing
    happens in the background; use the returned ``task_id`` to poll status.
    """
    _validate_media(file)

    task = AITask(
        task_type=TASK_TYPE,
        status="pending",
        progress=0,
        current_stage="uploading",
        input_data={"filename": file.filename},
        created_by=str(current_user.id),
    )
    db.add(task)
    await db.flush()

    logger.info(
        "Interview record generation task created: %s by user %s",
        task.id,
        current_user.id,
    )

    from app.services.storage_service import StorageService

    storage = StorageService()
    # Determine category based on file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    category = "audio" if f".{ext}" in ALLOWED_AUDIO_EXTENSIONS else "video"
    await storage.save_upload(file=file, category=category, user_id=str(current_user.id))

    background_tasks.add_task(_process_interview_record, task.id)

    return GenerateResponse(task_id=task.id)


@router.get(
    "/{record_id}",
    response_model=InterviewRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an interview record by ID",
)
async def get_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordResponse:
    """Return a single interview record."""
    result = await db.execute(
        select(InterviewRecord).where(
            InterviewRecord.id == record_id,
            InterviewRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(f"Interview record '{record_id}' not found")

    return InterviewRecordResponse.model_validate(record)


@router.put(
    "/{record_id}",
    response_model=InterviewRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an interview record",
)
async def update_record(
    record_id: str,
    body: InterviewRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewRecordResponse:
    """Update fields of an existing interview record."""
    result = await db.execute(
        select(InterviewRecord).where(
            InterviewRecord.id == record_id,
            InterviewRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundException(f"Interview record '{record_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.flush()
    await db.refresh(record)

    logger.info("Interview record %s updated by user %s", record_id, current_user.id)
    return InterviewRecordResponse.model_validate(record)


@router.get(
    "/{record_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download the generated interview record document",
)
async def download_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Return the generated Word/PDF document for the interview record."""
    from app.models.document import GeneratedDocument
    from app.models.file import UploadedFile

    # Verify the record exists
    result = await db.execute(
        select(InterviewRecord).where(
            InterviewRecord.id == record_id,
            InterviewRecord.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundException(f"Interview record '{record_id}' not found")

    # Find the generated document
    doc_result = await db.execute(
        select(GeneratedDocument)
        .join(UploadedFile, GeneratedDocument.uploaded_file_id == UploadedFile.id)
        .where(
            GeneratedDocument.source_entity_type == "interview_record",
            GeneratedDocument.source_entity_id == record_id,
        )
        .order_by(GeneratedDocument.version.desc())
    )
    generated_doc = doc_result.scalar_one_or_none()
    if generated_doc is None:
        raise NotFoundException("No generated document found for this record")

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
        "Interview record %s downloaded by user %s",
        record_id,
        current_user.id,
    )

    return FileResponse(
        path=file_path,
        filename=uploaded_file.original_name,
        media_type=uploaded_file.mime_type or "application/octet-stream",
    )
