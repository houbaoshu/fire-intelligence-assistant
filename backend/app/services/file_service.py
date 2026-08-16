"""File service: persist uploads to storage and record metadata."""
from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import StorageError
from app.models.file import UploadedFile
from app.services.storage.service import get_storage_service
from app.utils.file_validation import checksum_bytes, read_upload, validate_upload


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.storage = get_storage_service()

    def store_upload(self, file: UploadFile, category: str, user_id: uuid.UUID) -> UploadedFile:
        """Validate, persist and record an uploaded file.

        Returns the UploadedFile record (committed by the caller's transaction).
        """
        ext = validate_upload(file, category)
        data = read_upload(file)

        storage_dir = {
            "video": "uploads/videos",
            "audio": "uploads/audio",
            "image": "uploads/images",
            "document": "uploads/documents",
            "knowledge_source": "knowledge",
        }.get(category, "uploads")

        storage_path = f"{storage_dir}/{uuid.uuid4()}{ext}"
        self.storage.save_bytes(storage_path, data)

        record = UploadedFile(
            original_name=file.filename or "unnamed",
            storage_path=storage_path,
            storage_provider=self.storage.provider_name,
            mime_type=file.content_type,
            file_extension=ext,
            size_bytes=len(data),
            checksum=checksum_bytes(data),
            category=category,
            uploaded_by=user_id,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def store_bytes(self, data: bytes, category: str, original_name: str, user_id: uuid.UUID, mime: str | None = None) -> UploadedFile:
        """Store raw bytes (used for generated documents / extracted frames)."""
        from app.core.exceptions import FileTypeError
        from app.utils.file_validation import get_extension

        try:
            ext = get_extension(original_name)
        except FileTypeError:
            ext = ".bin"

        storage_path = f"generated/{uuid.uuid4()}{ext}"
        self.storage.save_bytes(storage_path, data)
        record = UploadedFile(
            original_name=original_name,
            storage_path=storage_path,
            storage_provider=self.storage.provider_name,
            mime_type=mime,
            file_extension=ext,
            size_bytes=len(data),
            checksum=checksum_bytes(data),
            category=category,
            uploaded_by=user_id,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def read(self, uploaded_file_id: uuid.UUID) -> bytes:
        record = self.db.get(UploadedFile, uploaded_file_id)
        if record is None or record.deleted_at is not None:
            raise StorageError("文件不存在")
        return self.storage.open_bytes(record.storage_path)

    def get_record(self, uploaded_file_id: uuid.UUID) -> UploadedFile | None:
        return self.db.get(UploadedFile, uploaded_file_id)
