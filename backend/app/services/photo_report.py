"""Photo report service."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import FileValidationException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.file import UploadedFile
from app.models.photo_report import PhotoReport
from app.models.task import AITask
from app.models.user import User
from app.schemas.photo_report import PhotoReportUpdate
from app.services.storage.factory import get_storage_service

logger = get_logger(__name__)

# Allowed video extensions and MIME types
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}


class PhotoReportService:
    """Service for photo report operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: Async database session.
        """
        self.db = db

    async def generate(
        self,
        video_file: UploadFile,
        user: User,
    ) -> AITask:
        """Validate file, save to storage, create task for background processing.

        Args:
            video_file: Uploaded video file.
            user: Current user.

        Returns:
            Created AITask.

        Raises:
            FileValidationException: If file is invalid.
        """
        logger.info("Photo report generation request", extra={"user_id": str(user.id)})

        # Validate file extension
        if not video_file.filename:
            raise FileValidationException("Filename is required")

        ext = (
            "." + video_file.filename.rsplit(".", 1)[-1].lower()
            if "." in video_file.filename
            else ""
        )
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise FileValidationException(
                f"Invalid file extension. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            )

        # Validate MIME type
        if video_file.content_type and video_file.content_type not in ALLOWED_VIDEO_MIMES:
            raise FileValidationException(
                f"Invalid MIME type. Allowed: {', '.join(ALLOWED_VIDEO_MIMES)}"
            )

        # Read file content
        content = await video_file.read()
        settings = get_settings()
        if len(content) > settings.max_upload_size_bytes:
            raise FileValidationException(
                f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Save to storage
        storage = get_storage_service()
        file_id = str(uuid4())
        storage_path = f"videos/{file_id}{ext}"
        await storage.upload(content, storage_path, video_file.content_type)

        # Create UploadedFile record
        uploaded_file = UploadedFile(
            id=file_id,
            original_name=video_file.filename,
            storage_path=storage_path,
            storage_provider=settings.storage_provider,
            mime_type=video_file.content_type,
            file_extension=ext,
            size_bytes=len(content),
            checksum=checksum,
            category="video",
            uploaded_by=str(user.id),
        )
        self.db.add(uploaded_file)

        # Create AITask
        task = AITask(
            task_type="photo_report_generation",
            status="pending",
            input_data={"file_id": file_id, "file_path": storage_path},
            created_by=str(user.id),
        )
        self.db.add(task)
        await self.db.flush()

        logger.info("Task created", extra={"task_id": task.id})

        return task

    async def get_report(self, report_id: str, user: User) -> PhotoReport:
        """Get photo report with images, verifying ownership.

        Args:
            report_id: Report UUID.
            user: Current user.

        Returns:
            PhotoReport with images loaded.

        Raises:
            NotFoundException: If report not found.
            ForbiddenException: If user doesn't own the report.
        """
        result = await self.db.execute(
            select(PhotoReport)
            .options(selectinload(PhotoReport.images))
            .where(PhotoReport.id == report_id)
        )
        report = result.scalar_one_or_none()

        if not report:
            raise NotFoundException("Photo report not found")

        if report.created_by != str(user.id):
            raise ForbiddenException("You do not have access to this report")

        return report

    async def update_report(
        self,
        report_id: str,
        data: PhotoReportUpdate,
        user: User,
    ) -> PhotoReport:
        """Update photo report fields and images.

        Args:
            report_id: Report UUID.
            data: Update data.
            user: Current user.

        Returns:
            Updated PhotoReport.

        Raises:
            NotFoundException: If report not found.
            ForbiddenException: If user doesn't own the report.
        """
        report = await self.get_report(report_id, user)

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        images_data = update_data.pop("images", None)

        for field, value in update_data.items():
            setattr(report, field, value)

        # Update images if provided
        if images_data is not None:
            for img_data in images_data:
                img_id = img_data.get("id")
                # Find matching image
                for img in report.images:
                    if img.id == img_id:
                        if "caption" in img_data:
                            img.caption = img_data["caption"]
                        if "detected_address" in img_data:
                            img.detected_address = img_data["detected_address"]
                        if "detected_violation" in img_data:
                            img.detected_violation = img_data["detected_violation"]
                        if "is_selected" in img_data:
                            img.is_selected = img_data["is_selected"]
                        if "sort_order" in img_data:
                            img.sort_order = img_data["sort_order"]
                        break

        await self.db.flush()

        # Reload with images
        return await self.get_report(report_id, user)

    async def get_download(self, report_id: str, user: User) -> str:
        """Get storage path for generated document.

        Args:
            report_id: Report UUID.
            user: Current user.

        Returns:
            Storage path for the document.

        Raises:
            NotFoundException: If report or document not found.
            ForbiddenException: If user doesn't own the report.
        """
        await self.get_report(report_id, user)

        # For now, return a placeholder path
        # In production, this would look up the GeneratedDocument
        raise NotFoundException("Document generation not yet implemented")
