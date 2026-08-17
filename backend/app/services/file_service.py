"""文件上传校验与保存（API.md §9 四重校验，ARCHITECTURE.md §15 目录分类）。

校验顺序：扩展名白名单 → MIME 与扩展名一致 → 文件签名（magic bytes）→ 大小上限。
类型不符 400 INVALID_FILE_TYPE，超限 413 FILE_TOO_LARGE；错误信息必须可读。
存储文件名一律 UUID 生成，不信任客户端文件名。
"""

import hashlib
import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.uploaded_file import UploadedFile
from app.repositories.file_repository import UploadedFileRepository
from app.services.storage import StorageService, get_storage_service

MB = 1024 * 1024

# 各类别扩展名 / MIME / 大小上限（API.md §9 表格为唯一权威定义，此处不得偏离）
_MIME_BY_EXT: dict[str, set[str]] = {
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "audio/m4a"},
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    },
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}

_CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "video": {".mp4", ".mov"},
    "image": {".jpg", ".jpeg", ".png"},
    "audio": {".wav", ".mp3", ".m4a"},
    "document": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"},
    # DATABASE.md uploaded_files.category 含 knowledge_source；规则同"文档"（API.md §9）
    "knowledge_source": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"},
}

_CATEGORY_MAX_BYTES: dict[str, int] = {
    "video": 500 * MB,
    "image": 20 * MB,
    "audio": 200 * MB,
    "document": 50 * MB,
    "knowledge_source": 50 * MB,
}

# ISO BMFF（mp4/mov/m4a）第 4~8 字节为 "ftyp"
_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _matches_magic(ext: str, head: bytes) -> bool:
    if ext in (".mp4", ".mov", ".m4a"):
        return len(head) >= 8 and head[4:8] == b"ftyp"
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == ".wav":
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if ext == ".mp3":
        return head.startswith(b"ID3") or (
            len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0
        )
    if ext == ".pdf":
        return head.startswith(b"%PDF")
    if ext in (".doc", ".ppt"):
        return head.startswith(_OLE2)
    if ext in (".docx", ".pptx"):
        return head.startswith(b"PK\x03\x04")
    if ext in (".txt", ".md"):
        return True  # 纯文本无文件签名
    return False


def invalid_file_type(message: str) -> AppException:
    return AppException("INVALID_FILE_TYPE", message, 400)


def file_too_large(message: str) -> AppException:
    return AppException("FILE_TOO_LARGE", message, 413)


class FileService:
    def __init__(self, session: Session, storage: StorageService | None = None) -> None:
        self.session = session
        self.files = UploadedFileRepository(session)
        self.storage = storage or get_storage_service()
        self.settings = get_settings()

    @staticmethod
    def validate(*, filename: str, content_type: str | None, data: bytes, category: str) -> str:
        """四重校验，返回小写扩展名；失败抛 400/413。"""
        if category not in _CATEGORY_EXTENSIONS:
            raise invalid_file_type(f"不支持的文件类别: {category}")

        # 1. 扩展名白名单
        ext = os.path.splitext(filename or "")[1].lower()
        allowed = _CATEGORY_EXTENSIONS[category]
        if ext not in allowed:
            readable = "、".join(sorted(allowed))
            raise invalid_file_type(f"文件扩展名 {ext or '(无)'} 不允许，该类文件仅支持：{readable}")

        # 2. MIME 与扩展名一致
        declared = (content_type or "").split(";")[0].strip().lower()
        if declared and declared not in _MIME_BY_EXT.get(ext, set()):
            raise invalid_file_type(
                f"文件类型 {declared} 与扩展名 {ext} 不一致"
            )

        # 3. 文件签名（magic bytes）与声明类型一致
        if not _matches_magic(ext, data[:16]):
            raise invalid_file_type(f"文件内容与声明的类型 {ext} 不符（文件签名校验失败）")

        # 4. 大小上限
        max_bytes = _CATEGORY_MAX_BYTES[category]
        if len(data) > max_bytes:
            raise file_too_large(
                f"文件大小 {len(data) / MB:.1f}MB 超过该类文件上限 {max_bytes // MB}MB"
            )
        if len(data) == 0:
            raise invalid_file_type("不允许上传空文件")
        return ext

    def save_upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
        category: str,
        uploaded_by: uuid.UUID,
        directory: str | None = None,
    ) -> UploadedFile:
        """校验并保存：文件本体进对象存储（默认 uploads/<category>/ 目录，
        可用 directory 覆盖），元数据入库（不提交事务）。"""
        ext = self.validate(
            filename=filename, content_type=content_type, data=data, category=category
        )
        prefix = directory or f"uploads/{category}"
        storage_key = f"{prefix}/{uuid.uuid4().hex}{ext}"
        self.storage.save(storage_key, data)
        try:
            file = UploadedFile(
                original_name=os.path.basename(filename or "unnamed"),
                storage_path=storage_key,
                storage_provider=self.settings.STORAGE_PROVIDER,
                mime_type=(content_type or "").split(";")[0].strip().lower() or None,
                file_extension=ext,
                size_bytes=len(data),
                checksum=hashlib.sha256(data).hexdigest(),
                category=category,
                uploaded_by=uploaded_by,
            )
            self.files.add(file)
        except Exception:
            # 元数据入库失败时尽力清理已写入的存储对象，避免孤儿文件
            self.storage.delete(storage_key)
            raise
        return file

    def save_generated(
        self, *, filename: str, data: bytes, uploaded_by: uuid.UUID
    ) -> UploadedFile:
        """保存后端生成的文档（generated/ 目录，category=generated_document，不提交事务）。"""
        ext = os.path.splitext(filename)[1].lower()
        storage_key = f"generated/{uuid.uuid4().hex}{ext}"
        self.storage.save(storage_key, data)
        file = UploadedFile(
            original_name=filename,
            storage_path=storage_key,
            storage_provider=self.settings.STORAGE_PROVIDER,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_extension=ext,
            size_bytes=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            category="generated_document",
            uploaded_by=uploaded_by,
        )
        return self.files.add(file)

    def read_bytes(self, file: UploadedFile) -> bytes:
        return self.storage.read(file.storage_path)
