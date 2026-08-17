"""Speech 能力服务（OpenAI 兼容 audio transcriptions API）。

职责：仅做音频/视频语音转写（AI_CONTEXT.md「Speech Recognition」）；
转写文本交 LLM 进一步处理。模型与地址一律来自环境变量配置。
"""

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import AIProviders

_MIME_BY_EXT = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
}


class SpeechService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or (
            OpenAICompatClient(
                base_url=self._settings.AI_SPEECH_BASE_URL,
                api_key=self._settings.AI_SPEECH_API_KEY,
                settings=self._settings,
                transport=transport,
            )
            if AIProviders(self._settings).is_configured("speech")
            else None
        )

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        """转写音频为文本；失败抛可读应用异常。不编造转写内容。"""
        if self._client is None:
            raise ai_not_configured("speech")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
        data = self._client.post_multipart(
            "/audio/transcriptions",
            data={"model": self._settings.AI_SPEECH_MODEL, "response_format": "json"},
            files={"file": (filename, audio_bytes, mime)},
        )
        try:
            text = data["text"]
        except (KeyError, TypeError):
            raise ai_service_error("AI 能力 speech 返回了无法解析的响应")
        if not isinstance(text, str):
            raise ai_service_error("AI 能力 speech 返回了非文本内容")
        return text.strip()
