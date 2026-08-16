"""File content endpoints (authorized access to stored files).

Download is served through controlled endpoints; internal storage paths are
never exposed to clients (specs/_common.md security rules).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.dependencies import CurrentUser, DB
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.file import UploadedFile
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])

MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


def _can_view_file(user, record: UploadedFile) -> bool:
    if user.role in ("admin", "supervisor"):
        return True
    if record.uploaded_by == user.id:
        return True
    # images inside a photo report created by the user are also accessible
    return False


@router.get("/{file_id}/content")
def file_content(user: CurrentUser, db: DB, file_id: uuid.UUID):
    record = db.get(UploadedFile, file_id)
    if record is None or record.deleted_at is not None:
        raise NotFoundError("文件不存在")
    if not _can_view_file(user, record):
        raise ForbiddenError("无权访问该文件")
    data = FileService(db).storage.open_bytes(record.storage_path)
    mime = record.mime_type or MIME_BY_EXT.get(record.file_extension or "", "application/octet-stream")
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{record.original_name}"'},
    )
