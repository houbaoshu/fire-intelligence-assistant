"""Photo report endpoints: generate, retrieve, update, and download."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import FileValidationException, NotFoundException
from app.core.logging import get_logger
from app.models.photo_report import PhotoReport
from app.models.task import AITask
from app.models.user import User
from app.schemas.inspection import GenerateResponse
from app.schemas.photo_report import PhotoReportResponse, PhotoReportUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["photo-report"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
TASK_TYPE = "photo_report_generation"


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


async def _process_photo_report(task_id: str) -> None:
    """Background task: run the full AI pipeline for photo report generation.

    This is a placeholder that will be replaced by the actual service
    implementation. The service will:
    1. Extract frames from the video
    2. Run vision analysis to detect violations
    3. Select and annotate images
    4. Generate the Word document
    5. Update the task status
    """
    from app.core.database import _get_session_factory
    from app.services.photo_report_service import PhotoReportService

    factory = _get_session_factory()
    async with factory() as db:
        try:
            service = PhotoReportService(db=db)
            await service.process_generation_task(task_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a photo report from video",
)
async def generate(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Video file (mp4/mov)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    """Upload a video and start async photo report generation.

    The video is validated, stored, and an AI task is created. Processing
    happens in the background; use the returned ``task_id`` to poll status.
    """
    _validate_video(file)

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
        "Photo report generation task created: %s by user %s",
        task.id,
        current_user.id,
    )

    from app.services.storage_service import StorageService

    storage = StorageService()
    await storage.save_upload(file=file, category="video", user_id=str(current_user.id))

    background_tasks.add_task(_process_photo_report, task.id)

    return GenerateResponse(task_id=task.id)


@router.get(
    "/{report_id}",
    response_model=PhotoReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a photo report by ID",
)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoReportResponse:
    """Return a single photo report with its images."""
    result = await db.execute(
        select(PhotoReport)
        .options(selectinload(PhotoReport.images))
        .where(
            PhotoReport.id == report_id,
            PhotoReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundException(f"Photo report '{report_id}' not found")

    return PhotoReportResponse.model_validate(report)


@router.put(
    "/{report_id}",
    response_model=PhotoReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a photo report",
)
async def update_report(
    report_id: str,
    body: PhotoReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoReportResponse:
    """Update fields and/or images of an existing photo report."""

    result = await db.execute(
        select(PhotoReport)
        .options(selectinload(PhotoReport.images))
        .where(
            PhotoReport.id == report_id,
            PhotoReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundException(f"Photo report '{report_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    images_data = update_data.pop("images", None)

    for field, value in update_data.items():
        setattr(report, field, value)

    if images_data is not None:
        # Update individual image fields by ID
        for image_update in images_data:
            img_data = (
                image_update
                if isinstance(image_update, dict)
                else image_update.model_dump(exclude_unset=True)
            )
            image_id = img_data.pop("id", None)
            if image_id is None:
                continue

            # Find the existing image
            existing = next((img for img in report.images if img.id == image_id), None)
            if existing is None:
                continue

            for field, value in img_data.items():
                if value is not None:
                    setattr(existing, field, value)

    await db.flush()

    # Re-fetch to get updated data
    result = await db.execute(
        select(PhotoReport)
        .options(selectinload(PhotoReport.images))
        .where(PhotoReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    logger.info("Photo report %s updated by user %s", report_id, current_user.id)
    return PhotoReportResponse.model_validate(report)


@router.get(
    "/{report_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download the generated photo report document",
)
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Return the generated Word/PDF document for the photo report."""
    from app.models.document import GeneratedDocument
    from app.models.file import UploadedFile

    # Verify the report exists
    result = await db.execute(
        select(PhotoReport).where(
            PhotoReport.id == report_id,
            PhotoReport.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise NotFoundException(f"Photo report '{report_id}' not found")

    # Find the generated document
    doc_result = await db.execute(
        select(GeneratedDocument)
        .join(UploadedFile, GeneratedDocument.uploaded_file_id == UploadedFile.id)
        .where(
            GeneratedDocument.source_entity_type == "photo_report",
            GeneratedDocument.source_entity_id == report_id,
        )
        .order_by(GeneratedDocument.version.desc())
    )
    generated_doc = doc_result.scalar_one_or_none()
    if generated_doc is None:
        raise NotFoundException("No generated document found for this report")

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
        "Photo report %s downloaded by user %s",
        report_id,
        current_user.id,
    )

    return FileResponse(
        path=file_path,
        filename=uploaded_file.original_name,
        media_type=uploaded_file.mime_type or "application/octet-stream",
    )
