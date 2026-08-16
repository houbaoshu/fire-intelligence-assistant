"""Speech recognition service (OpenAI-compatible /audio/transcriptions)."""
from __future__ import annotations

from app.core.config import get_settings

from .client import AIProviderClient


class SpeechService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def model(self) -> str | None:
        from app.services.aiplatform.router import resolve_model

        return resolve_model("speech")

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        return self.client.audio_transcription(self.model or "", audio_bytes, filename)
