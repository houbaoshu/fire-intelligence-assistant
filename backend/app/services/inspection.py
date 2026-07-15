"""Inspection record service."""

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
from app.models.inspection import InspectionRecord, InspectionRecordItem
from app.models.task import AITask
from app.models.user import User
from app.schemas.inspection import InspectionRecordUpdate
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


class InspectionRecordService:
    """Service for inspection record operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session.

        Args:
            db: Async database session.
        """
        self.db = db

    async def generate(
        self,
        video_file: UploadFile,
        remarks: str | None,
        user: User,
    ) -> AITask:
        """Validate file, save to storage, create task for background processing.

        Args:
            video_file: Uploaded video file.
            remarks: Optional user remarks.
            user: Current user.

        Returns:
            Created AITask.

        Raises:
            FileValidationException: If file is invalid.
        """
        logger.info("Inspection generation request", extra={"user_id": str(user.id)})

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
            task_type="inspection_record_generation",
            status="pending",
            input_data={"file_id": file_id, "file_path": storage_path, "remarks": remarks},
            created_by=str(user.id),
        )
        self.db.add(task)
        await self.db.flush()

        logger.info("Task created", extra={"task_id": task.id})

        return task

    async def get_record(self, record_id: str, user: User) -> InspectionRecord:
        """Get inspection record with items, verifying ownership.

        Args:
            record_id: Record UUID.
            user: Current user.

        Returns:
            InspectionRecord with items loaded.

        Raises:
            NotFoundException: If record not found.
            ForbiddenException: If user doesn't own the record.
        """
        result = await self.db.execute(
            select(InspectionRecord)
            .options(selectinload(InspectionRecord.items))
            .where(InspectionRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise NotFoundException("Inspection record not found")

        if record.created_by != str(user.id):
            raise ForbiddenException("You do not have access to this record")

        return record

    async def update_record(
        self,
        record_id: str,
        data: InspectionRecordUpdate,
        user: User,
    ) -> InspectionRecord:
        """Update inspection record fields and items.

        Args:
            record_id: Record UUID.
            data: Update data.
            user: Current user.

        Returns:
            Updated InspectionRecord.

        Raises:
            NotFoundException: If record not found.
            ForbiddenException: If user doesn't own the record.
        """
        record = await self.get_record(record_id, user)

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        items_data = update_data.pop("items", None)

        for field, value in update_data.items():
            setattr(record, field, value)

        # Update items if provided
        if items_data is not None:
            # Delete existing items
            for item in record.items:
                await self.db.delete(item)

            # Create new items
            for idx, item_data in enumerate(items_data):
                item = InspectionRecordItem(
                    inspection_record_id=record.id,
                    item_type=item_data.get("item_type", "observation"),
                    location=item_data.get("location"),
                    description=item_data.get("description", ""),
                    legal_basis=item_data.get("legal_basis"),
                    correction_requirement=item_data.get("correction_requirement"),
                    severity=item_data.get("severity"),
                    sort_order=item_data.get("sort_order", idx),
                )
                self.db.add(item)

        await self.db.flush()

        # Reload with items
        return await self.get_record(record_id, user)

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
