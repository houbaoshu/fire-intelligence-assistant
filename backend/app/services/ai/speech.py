"""Speech 能力服务（OpenAI 兼容 audio transcriptions API）。

职责：仅做音频/视频语音转写（AI_CONTEXT.md「Speech Recognition」）；
转写文本交 LLM 进一步处理。模型与地址经模型路由解析（providers.py：DB 生效配置优先，回退环境变量）。

接口风格由 ``AI_SPEECH_API_STYLE`` 选择：
``transcriptions``（默认，Whisper 风格 multipart /audio/transcriptions）；
``chat_completions``（百炼等无该端点的兼容服务，走 /chat/completions + input_audio）。
"""

import base64
import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import resolve_capability_config

_MIME_BY_EXT = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
}


def _to_wav_bytes(audio_bytes: bytes) -> bytes:
    """转码为 16kHz 单声道 WAV（复用 media 模块的 ffmpeg 封装）。"""
    from app.services.media.video import MediaProcessingError, extract_audio

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "input.audio"
        dst = Path(tmp) / "output.wav"
        src.write_bytes(audio_bytes)
        try:
            extract_audio(src, dst)
        except MediaProcessingError as exc:
            raise ai_service_error(f"音频转码失败：{exc}")
        return dst.read_bytes()


class SpeechService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
        session: Session | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        config = (
            None
            if client is not None
            else resolve_capability_config("speech", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_SPEECH_MODEL
        self._client = client or (
            OpenAICompatClient(
                base_url=config.base_url,
                api_key=config.api_key,
                settings=self._settings,
                transport=transport,
            )
            if config
            else None
        )

    def transcribe(self, audio_bytes: bytes, *, filename: str = "audio.wav") -> str:
        """转写音频为文本；失败抛可读应用异常。不编造转写内容。"""
        if self._client is None:
            raise ai_not_configured("speech")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
        if self._settings.AI_SPEECH_API_STYLE == "chat_completions":
            return self._transcribe_via_chat(audio_bytes, mime)
        data = self._client.post_multipart(
            "/audio/transcriptions",
            data={"model": self._model, "response_format": "json"},
            files={"file": (filename, audio_bytes, mime)},
        )
        try:
            text = data["text"]
        except (KeyError, TypeError):
            raise ai_service_error("AI 能力 speech 返回了无法解析的响应")
        if not isinstance(text, str):
            raise ai_service_error("AI 能力 speech 返回了非文本内容")
        return text.strip()

    def _transcribe_via_chat(self, audio_bytes: bytes, mime: str) -> str:
        """百炼等兼容端点：无 /audio/transcriptions，走 /chat/completions
        + input_audio（base64 data URI，限 10MB / 5 分钟，模型如 qwen3-asr-flash）。
        该路径对容器格式敏感（m4a/aac 直传会被拒），统一转 16kHz 单声道 WAV。"""
        if mime != "audio/wav":
            audio_bytes = _to_wav_bytes(audio_bytes)
            mime = "audio/wav"
        data_uri = f"data:{mime};base64,{base64.b64encode(audio_bytes).decode()}"
        data = self._client.post_json(
            "/chat/completions",
            {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_audio", "input_audio": {"data": data_uri}}
                        ],
                    }
                ],
                "stream": False,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ai_service_error("AI 能力 speech 返回了无法解析的响应")
        if not isinstance(content, str):
            raise ai_service_error("AI 能力 speech 返回了非文本内容")
        return content.strip()
