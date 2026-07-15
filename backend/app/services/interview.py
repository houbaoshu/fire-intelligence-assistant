"""Interview record service."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FileValidationException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.file import UploadedFile
from app.models.interview import InterviewRecord
from app.models.task import AITask
from app.models.user import User
from app.schemas.interview import InterviewRecordUpdate
from app.services.storage.factory import get_storage_service

logger = get_logger(__name__)

# Allowed media extensions and MIME types
ALLOWED_MEDIA_EXTENSIONS = {".mp4", ".mp3", ".wav", ".m4a", ".mov", ".avi"}
ALLOWED_MEDIA_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
}


class InterviewRecordService:
    """Service for interview record operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: Async database session.
        """
        self.db = db

    async def generate(
        self,
        media_file: UploadFile,
        user: User,
    ) -> AITask:
        """Validate file, save to storage, create task for background processing.

        Args:
            media_file: Uploaded audio or video file.
            user: Current user.

        Returns:
            Created AITask.

        Raises:
            FileValidationException: If file is invalid.
        """
        logger.info("Interview generation request", extra={"user_id": str(user.id)})

        # Validate file extension
        if not media_file.filename:
            raise FileValidationException("Filename is required")

        ext = (
            "." + media_file.filename.rsplit(".", 1)[-1].lower()
            if "." in media_file.filename
            else ""
        )
        if ext not in ALLOWED_MEDIA_EXTENSIONS:
            raise FileValidationException(
                f"Invalid file extension. Allowed: {', '.join(ALLOWED_MEDIA_EXTENSIONS)}"
            )

        # Validate MIME type
        if media_file.content_type and media_file.content_type not in ALLOWED_MEDIA_MIMES:
            raise FileValidationException(
                f"Invalid MIME type. Allowed: {', '.join(ALLOWED_MEDIA_MIMES)}"
            )

        # Read file content
        content = await media_file.read()
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
        storage_path = f"audio/{file_id}{ext}"
        await storage.upload(content, storage_path, media_file.content_type)

        # Create UploadedFile record
        uploaded_file = UploadedFile(
            id=file_id,
            original_name=media_file.filename,
            storage_path=storage_path,
            storage_provider=settings.storage_provider,
            mime_type=media_file.content_type,
            file_extension=ext,
            size_bytes=len(content),
            checksum=checksum,
            category="audio",
            uploaded_by=str(user.id),
        )
        self.db.add(uploaded_file)

        # Create AITask
        task = AITask(
            task_type="interview_record_generation",
            status="pending",
            input_data={"file_id": file_id, "file_path": storage_path},
            created_by=str(user.id),
        )
        self.db.add(task)
        await self.db.flush()

        logger.info("Task created", extra={"task_id": task.id})

        return task

    async def get_record(self, record_id: str, user: User) -> InterviewRecord:
        """Get interview record, verifying ownership.

        Args:
            record_id: Record UUID.
            user: Current user.

        Returns:
            InterviewRecord.

        Raises:
            NotFoundException: If record not found.
            ForbiddenException: If user doesn't own the record.
        """
        result = await self.db.execute(
            select(InterviewRecord).where(InterviewRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise NotFoundException("Interview record not found")

        if record.created_by != str(user.id):
            raise ForbiddenException("You do not have access to this record")

        return record

    async def update_record(
        self,
        record_id: str,
        data: InterviewRecordUpdate,
        user: User,
    ) -> InterviewRecord:
        """Update interview record fields.

        Args:
            record_id: Record UUID.
            data: Update data.
            user: Current user.

        Returns:
            Updated InterviewRecord.

        Raises:
            NotFoundException: If record not found.
            ForbiddenException: If user doesn't own the record.
        """
        record = await self.get_record(record_id, user)

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)

        await self.db.flush()

        return record

    async def get_download(self, record_id: str, user: User) -> str:
        """Get storage path for generated document.

        Args:
            record_id: Record UUID.
            user: Current user.

        Returns:
            Storage path for the document.

        Raises:
            NotFoundException: If record or document not found.
            ForbiddenException: If user doesn't own the record.
        """
        await self.get_record(record_id, user)

        # For now, return a placeholder path
        # In production, this would look up the GeneratedDocument
        raise NotFoundException("Document generation not yet implemented")
