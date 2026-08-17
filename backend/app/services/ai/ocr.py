"""OCR 能力服务（OpenAI 兼容多模态 chat completions）。

职责：仅从图像中提取文字并保留原始内容（AI_CONTEXT.md「OCR」）；
推理归 LLM。模型与地址一律来自环境变量配置。
"""

import base64

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import AIProviders

# OCR 的固定指令：只转录图像中的文字，不做任何解释或补全
_OCR_INSTRUCTION = (
    "请转录这张图片中出现的全部文字。只输出图片中真实存在的文字原文，"
    "保持原有顺序与换行；不要解释、翻译或补全。图片中没有文字时输出空字符串。"
)


class OCRService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or (
            OpenAICompatClient(
                base_url=self._settings.AI_OCR_BASE_URL,
                api_key=self._settings.AI_OCR_API_KEY,
                settings=self._settings,
                transport=transport,
            )
            if AIProviders(self._settings).is_configured("ocr")
            else None
        )

    def extract_text(self, image_bytes: bytes) -> str:
        """从图像中提取文字；无文字时返回空字符串。失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("ocr")
        url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        data = self._client.post_json(
            "/chat/completions",
            {
                "model": self._settings.AI_OCR_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _OCR_INSTRUCTION},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                "temperature": 0,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ai_service_error("AI 能力 ocr 返回了无法解析的响应")
        if not isinstance(content, str):
            raise ai_service_error("AI 能力 ocr 返回了非文本内容")
        return content.strip()
