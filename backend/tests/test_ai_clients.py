"""Vision/OCR/Speech 能力客户端测试（httpx.MockTransport，不触网）。

覆盖：请求构造（模型/base_url/密钥全来自配置）、正常解析、
未配置可读失败、HTTP 错误与重试、畸形响应。
"""

import json

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import AppException
from app.services.ai.ocr import OCRService
from app.services.ai.speech import SpeechService
from app.services.ai.vision import VisionService

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _settings(**overrides) -> Settings:
    base = {
        "AI_VISION_API_KEY": "vision-key",
        "AI_VISION_MODEL": "vision-model",
        "AI_VISION_BASE_URL": "https://vision.example.com/v1",
        "AI_OCR_API_KEY": "ocr-key",
        "AI_OCR_MODEL": "ocr-model",
        "AI_OCR_BASE_URL": "https://ocr.example.com/v1",
        "AI_SPEECH_API_KEY": "speech-key",
        "AI_SPEECH_MODEL": "speech-model",
        "AI_SPEECH_BASE_URL": "https://speech.example.com/v1",
        "AI_HTTP_MAX_RETRIES": 0,
    }
    base.update(overrides)
    return Settings(**base)


def _chat_transport(body: str, requests: list[httpx.Request] | None = None, status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if status == 200:
            content = {"choices": [{"message": {"content": body}}]}
            return httpx.Response(200, json=content)
        return httpx.Response(status, json={"error": "boom"})

    return httpx.MockTransport(handler)


# ---------- Vision ----------


def test_vision_request_shape_and_response():
    requests: list[httpx.Request] = []
    service = VisionService(
        settings=_settings(), transport=_chat_transport("画面描述", requests)
    )
    result = service.analyze_image("分析这张图", image_bytes=PNG_BYTES)
    assert result == "画面描述"

    request = requests[0]
    assert request.url == "https://vision.example.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer vision-key"
    payload = json.loads(request.content)
    assert payload["model"] == "vision-model"
    content = payload["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "分析这张图"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_vision_accepts_external_image_url():
    requests: list[httpx.Request] = []
    service = VisionService(
        settings=_settings(), transport=_chat_transport("ok", requests)
    )
    service.analyze_image("p", image_url="https://img.example.com/a.jpg")
    payload = json.loads(requests[0].content)
    assert payload["messages"][0]["content"][1]["image_url"]["url"] == (
        "https://img.example.com/a.jpg"
    )


def test_vision_not_configured():
    service = VisionService(settings=_settings(AI_VISION_API_KEY=""))
    with pytest.raises(AppException) as exc_info:
        service.analyze_image("p", image_bytes=PNG_BYTES)
    assert exc_info.value.code == "AI_SERVICE_NOT_CONFIGURED"


def test_vision_rejected_request_is_readable():
    service = VisionService(
        settings=_settings(), transport=_chat_transport("", status=401)
    )
    with pytest.raises(AppException) as exc_info:
        service.analyze_image("p", image_bytes=PNG_BYTES)
    assert exc_info.value.code == "AI_SERVICE_ERROR"
    assert "401" in exc_info.value.message


def test_vision_malformed_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    service = VisionService(settings=_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(AppException) as exc_info:
        service.analyze_image("p", image_bytes=PNG_BYTES)
    assert exc_info.value.code == "AI_SERVICE_ERROR"


# ---------- OCR ----------


def test_ocr_request_shape_and_response():
    requests: list[httpx.Request] = []
    service = OCRService(
        settings=_settings(), transport=_chat_transport("  安全出口标识  ", requests)
    )
    assert service.extract_text(PNG_BYTES) == "安全出口标识"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "ocr-model"
    assert payload["messages"][0]["content"][1]["type"] == "image_url"


def test_ocr_not_configured():
    service = OCRService(settings=_settings(AI_OCR_BASE_URL=""))
    with pytest.raises(AppException) as exc_info:
        service.extract_text(PNG_BYTES)
    assert exc_info.value.code == "AI_SERVICE_NOT_CONFIGURED"


# ---------- Speech ----------


def test_speech_request_shape_and_response():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"text": "转写文本"})

    service = SpeechService(settings=_settings(), transport=httpx.MockTransport(handler))
    assert service.transcribe(b"RIFF....", filename="a.wav") == "转写文本"

    request = requests[0]
    assert request.url == "https://speech.example.com/v1/audio/transcriptions"
    assert request.headers["Authorization"] == "Bearer speech-key"
    body = request.content.decode("utf-8", errors="replace")
    assert 'name="model"' in body and "speech-model" in body
    assert 'name="file"; filename="a.wav"' in body


def test_speech_not_configured():
    service = SpeechService(settings=_settings(AI_SPEECH_MODEL=""))
    with pytest.raises(AppException) as exc_info:
        service.transcribe(b"RIFF....")
    assert exc_info.value.code == "AI_SERVICE_NOT_CONFIGURED"


def test_speech_malformed_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    service = SpeechService(settings=_settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(AppException) as exc_info:
        service.transcribe(b"RIFF....")
    assert exc_info.value.code == "AI_SERVICE_ERROR"


# ---------- 重试 ----------


def test_retry_on_5xx_then_success():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(500, json={})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    service = VisionService(
        settings=_settings(AI_HTTP_MAX_RETRIES=1),
        transport=httpx.MockTransport(handler),
    )
    assert service.analyze_image("p", image_bytes=PNG_BYTES) == "ok"
    assert len(attempts) == 2
