import os
import uuid
from datetime import UTC, datetime

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}

VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}
AUDIO_MIME_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a"}
DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_file_mime(mime_type: str, allowed_mimes: set[str]) -> bool:
    return mime_type in allowed_mimes


def generate_storage_path(category: str, original_filename: str) -> str:
    """Generate a unique storage path for an uploaded file"""
    now = datetime.now(UTC)
    ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"{category}/{now.year}/{now.month:02d}/{now.day:02d}/{unique_name}"


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
