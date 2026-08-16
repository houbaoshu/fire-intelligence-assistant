"""Upload validation per API.md §9.

Every upload endpoint validates in order:
1. extension whitelist
2. MIME type matches extension
3. file signature (magic bytes) matches declared type
4. size limit

Any failure is rejected with a readable error (no silent ignore).
"""
from __future__ import annotations

import hashlib
import re

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, FileTypeError

# category -> (extensions, max_size_bytes)
ALLOWED_VIDEO_EXTS = {".mp4", ".mov"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".m4a"}
ALLOWED_DOC_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}

MIME_MAP = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
}

# Minimal magic-byte signatures (substring match on the first 16 bytes)
SIGNATURES: dict[str, list[bytes]] = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".docx": [b"PK\x03\x04"],
    ".pptx": [b"PK\x03\x04"],
    ".mp4": [b"\x00\x00\x00", b"ftyp", b"moov", b"mdat"],
    ".mov": [b"\x00\x00\x00", b"ftyp", b"moov", b"mdat"],
    ".m4a": [b"\x00\x00\x00", b"ftyp"],
    ".wav": [b"RIFF", b"WAVE"],
    ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
}

EXT_RE = re.compile(r"\.([a-zA-Z0-9]+)$")


def get_extension(filename: str) -> str:
    m = EXT_RE.search(filename)
    if not m:
        raise FileTypeError("文件名缺少扩展名")
    ext = "." + m.group(1).lower()
    if ext == ".jpeg":
        return ".jpg"
    return ext


def max_size_for(category: str) -> int:
    s = get_settings()
    mb = {
        "video": s.MAX_VIDEO_SIZE_MB,
        "audio": s.MAX_AUDIO_SIZE_MB,
        "document": s.MAX_DOC_SIZE_MB,
        "image": s.MAX_IMAGE_SIZE_MB,
    }.get(category, s.MAX_DOC_SIZE_MB)
    return mb * 1024 * 1024


def _matches_any_signature(data: bytes, ext: str) -> bool:
    sigs = SIGNATURES.get(ext)
    if not sigs:
        return True  # no signature defined for this type
    head = data[:16]
    for sig in sigs:
        if sig in head:
            return True
    return False


def validate_upload(file: UploadFile, category: str) -> str:
    """Validate extension, MIME, signature and size. Returns canonical extension.

    Raises FileTypeError / FileTooLargeError with readable messages.
    """
    ext = get_extension(file.filename or "")

    allowed = {
        "video": ALLOWED_VIDEO_EXTS,
        "audio": ALLOWED_AUDIO_EXTS,
        "document": ALLOWED_DOC_EXTS,
        "image": ALLOWED_IMAGE_EXTS,
    }.get(category, ALLOWED_DOC_EXTS)
    if ext not in allowed:
        raise FileTypeError(
            f"不支持的文件类型 .{ext.lstrip('.')},允许:{', '.join(sorted(e.lstrip('.') for e in allowed))}"
        )

    declared_mime = (file.content_type or "").lower()
    expected_mime = MIME_MAP.get(ext, "")
    if expected_mime and declared_mime and declared_mime != "application/octet-stream":
        # allow application/octet-stream as an untyped fallback, but reject clear mismatches
        if declared_mime != expected_mime:
            raise FileTypeError("文件类型与扩展名不一致")

    data = file.file.read(16)
    file.file.seek(0)
    if not _matches_any_signature(data, ext):
        raise FileTypeError("文件内容与声明类型不符,请检查文件是否完整")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > max_size_for(category):
        raise FileTooLargeError(f"文件过大(最大 {max_size_for(category) // (1024 * 1024)}MB)")
    return ext


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_upload(file: UploadFile) -> bytes:
    """Read the whole upload into memory (sizes are bounded by validation)."""
    return file.file.read()
