"""OCR service: extract text from images (transcription only; reasoning is LLM's job)."""
from __future__ import annotations

from app.core.config import get_settings

from .client import AIProviderClient

OCR_PROMPT = (
    "你是 OCR 引擎。请逐字转写图片中的全部可见文字,保留原始内容与格式。"
    "只输出识别到的文字本身,不要添加任何解释、推测或格式化标记。"
    "如果图片中没有可辨识的文字,输出空字符串。"
)


class OCRService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def model(self) -> str | None:
        from app.services.aiplatform.router import resolve_model

        return resolve_model("ocr") or get_settings().VISION_MODEL

    def extract_text(self, image_bytes: bytes, image_mime: str = "image/jpeg") -> str:
        return self.client.chat_vision(self.model or "", OCR_PROMPT, image_bytes, image_mime)
