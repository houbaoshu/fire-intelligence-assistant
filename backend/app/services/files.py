from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models import UploadedFile
from app.services.storage import StorageProvider


def validate_upload(
    upload: UploadFile,
    *,
    extensions: frozenset[str],
    max_bytes: int,
    allowed_mime_prefixes: tuple[str, ...] = (),
) -> tuple[str, int, str]:
    name = Path(upload.filename or "upload").name
    extension = Path(name).suffix.lower()
    if extension not in extensions:
        raise AppError(
            status_code=415,
            code="UNSUPPORTED_FILE_TYPE",
            message=f"Supported file types: {', '.join(sorted(extensions))}.",
        )
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    if size <= 0:
        raise AppError(status_code=422, code="EMPTY_FILE", message="The uploaded file is empty.")
    if size > max_bytes:
        raise AppError(
            status_code=413,
            code="FILE_TOO_LARGE",
            message=f"The file exceeds the {max_bytes // (1024 * 1024)} MB limit.",
        )
    mime = (upload.content_type or "application/octet-stream").lower()
    if allowed_mime_prefixes and not any(
        mime.startswith(prefix) for prefix in allowed_mime_prefixes
    ):
        raise AppError(
            status_code=415,
            code="INVALID_MIME_TYPE",
            message="The uploaded file content type does not match the selected workflow.",
        )
    digest = hashlib.sha256()
    while block := upload.file.read(1024 * 1024):
        digest.update(block)
    upload.file.seek(0)
    return extension, size, digest.hexdigest()


def persist_upload(
    session: Session,
    storage: StorageProvider,
    upload: UploadFile,
    *,
    user_id: uuid.UUID,
    category: str,
    storage_category: str,
    extensions: frozenset[str],
    max_bytes: int,
    allowed_mime_prefixes: tuple[str, ...] = (),
) -> UploadedFile:
    extension, _, checksum = validate_upload(
        upload,
        extensions=extensions,
        max_bytes=max_bytes,
        allowed_mime_prefixes=allowed_mime_prefixes,
    )
    stored = storage.save(
        category=storage_category,
        filename=upload.filename or f"upload{extension}",
        source=upload.file,
    )
    record = UploadedFile(
        original_name=Path(upload.filename or "upload").name,
        storage_path=stored.path,
        storage_provider="local",
        mime_type=upload.content_type,
        file_extension=extension,
        size_bytes=stored.size_bytes,
        checksum=checksum,
        category=category,
        uploaded_by=user_id,
    )
    session.add(record)
    session.flush()
    return record
