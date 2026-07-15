"""Speech-to-text transcription service."""

from __future__ import annotations

import openai

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpeechService:
    """Speech recognition service using OpenAI-compatible Whisper API.

    Transcribes audio files to text.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise AppException(
                "AI service is not configured. Please set OPENAI_API_KEY.",
                details={"code": "AI_NOT_CONFIGURED"},
            )
        self._client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Transcribed text.
        """
        logger.info("Speech transcription request", extra={"audio": audio_path})

        with open(audio_path, "rb") as audio_file:
            response = await self._client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh",
            )

        return response.text
