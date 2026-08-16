"""Vision service: image understanding for fire-safety inspection analysis."""
from __future__ import annotations

from app.core.config import get_settings

from .client import AIProviderClient


class VisionService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def model(self) -> str | None:
        from app.services.aiplatform.router import resolve_model

        return resolve_model("vision")

    def analyze_image(self, prompt: str, image_bytes: bytes, image_mime: str = "image/jpeg") -> str:
        return self.client.chat_vision(self.model or "", prompt, image_bytes, image_mime)
