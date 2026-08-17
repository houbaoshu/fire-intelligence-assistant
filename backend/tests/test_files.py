"""文件上传四重校验测试（API.md §9）。

直接单测 FileService.validate，不经 HTTP（HTTP 路径在记录 generate 测试中覆盖）。
"""

import pytest

from app.core.exceptions import AppException
from app.services.file_service import FileService

from .helpers import FAKE_MP3, FAKE_MP4, FAKE_PNG, FAKE_WAV


def test_valid_video_passes():
    ext = FileService.validate(
        filename="scene.mp4", content_type="video/mp4", data=FAKE_MP4, category="video"
    )
    assert ext == ".mp4"


def test_wrong_extension_rejected():
    with pytest.raises(AppException) as exc:
        FileService.validate(
            filename="evil.exe", content_type="video/mp4", data=FAKE_MP4, category="video"
        )
    assert exc.value.code == "INVALID_FILE_TYPE"
    assert exc.value.status_code == 400
    assert exc.value.message  # 可读


def test_extension_case_insensitive():
    ext = FileService.validate(
        filename="scene.MP4", content_type="video/mp4", data=FAKE_MP4, category="video"
    )
    assert ext == ".mp4"


def test_mime_mismatch_rejected():
    with pytest.raises(AppException) as exc:
        FileService.validate(
            filename="scene.mp4",
            content_type="application/pdf",
            data=FAKE_MP4,
            category="video",
        )
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_magic_bytes_mismatch_rejected():
    """伪造扩展名：wav 内容伪装成 mp4。"""
    with pytest.raises(AppException) as exc:
        FileService.validate(
            filename="fake.mp4", content_type="video/mp4", data=FAKE_WAV, category="video"
        )
    assert exc.value.code == "INVALID_FILE_TYPE"
    assert "签名" in exc.value.message


def test_text_file_without_magic_passes():
    FileService.validate(
        filename="notes.md", content_type="text/markdown", data=b"# hello", category="document"
    )
    FileService.validate(
        filename="notes.txt", content_type="text/plain", data=b"hello", category="document"
    )


def test_audio_and_image_categories():
    FileService.validate(filename="a.wav", content_type="audio/wav", data=FAKE_WAV, category="audio")
    FileService.validate(filename="a.mp3", content_type="audio/mpeg", data=FAKE_MP3, category="audio")
    FileService.validate(filename="a.png", content_type="image/png", data=FAKE_PNG, category="image")


def test_oversize_rejected(monkeypatch):
    import app.services.file_service as fs

    monkeypatch.setitem(fs._CATEGORY_MAX_BYTES, "video", 10)
    with pytest.raises(AppException) as exc:
        FileService.validate(
            filename="big.mp4", content_type="video/mp4", data=FAKE_MP4, category="video"
        )
    assert exc.value.code == "FILE_TOO_LARGE"
    assert exc.value.status_code == 413


def test_empty_file_rejected():
    with pytest.raises(AppException) as exc:
        FileService.validate(
            filename="a.mp4", content_type="video/mp4", data=b"", category="video"
        )
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_unknown_category_rejected():
    with pytest.raises(AppException):
        FileService.validate(
            filename="a.mp4", content_type="video/mp4", data=FAKE_MP4, category="unknown"
        )


def test_generate_endpoint_rejects_bad_file(client):
    """HTTP 路径：伪造 magic bytes 的上传返回 400 INVALID_FILE_TYPE。"""
    from .helpers import auth_headers, register

    tokens = register(client)
    resp = client.post(
        "/api/inspection-record/generate",
        headers=auth_headers(tokens),
        files={"video": ("fake.mp4", FAKE_WAV, "video/mp4")},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "INVALID_FILE_TYPE"
    assert body["error"]["message"]
