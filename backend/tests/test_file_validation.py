"""File upload validation tests (API.md §9)."""
from __future__ import annotations

import io

from fastapi import UploadFile

from app.core.exceptions import FileTooLargeError, FileTypeError
from app.utils.file_validation import validate_upload


def _upload(name: str, data: bytes, mime: str) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data), headers={"content-type": mime})


def test_valid_pdf():
    u = _upload("law.pdf", b"%PDF-1.4\n...content", "application/pdf")
    assert validate_upload(u, "document") == ".pdf"


def test_bad_extension():
    u = _upload("evil.exe", b"MZ...", "application/octet-stream")
    try:
        validate_upload(u, "document")
        assert False
    except FileTypeError as e:
        assert "不支持的文件类型" in str(e)


def test_mime_mismatch():
    u = _upload("law.pdf", b"%PDF-1.4", "image/png")
    try:
        validate_upload(u, "document")
        assert False
    except FileTypeError as e:
        assert "不一致" in str(e)


def test_signature_mismatch():
    u = _upload("fake.pdf", b"not a real pdf at all", "application/pdf")
    try:
        validate_upload(u, "document")
        assert False
    except FileTypeError:
        pass


def test_video_audio_categories():
    u = _upload("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")
    assert validate_upload(u, "video") == ".mp4"
    u = _upload("rec.wav", b"RIFF\x00\x00\x00\x00WAVEfmt", "audio/wav")
    assert validate_upload(u, "audio") == ".wav"


def test_oversize(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "MAX_DOC_SIZE_MB", 0)
    u = _upload("big.pdf", b"%PDF-1.4" + b"0" * 1024, "application/pdf")
    try:
        validate_upload(u, "document")
        assert False
    except FileTooLargeError:
        pass
