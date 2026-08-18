"""OCR 能力服务（OpenAI 兼容多模态 chat completions）。

职责：仅从图像中提取文字并保留原始内容（AI_CONTEXT.md「OCR」）；
推理归 LLM。模型与地址经模型路由解析（providers.py：DB 生效配置优先，回退环境变量）。
"""

import base64

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import resolve_capability_config

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
        session: Session | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        config = (
            None
            if client is not None
            else resolve_capability_config("ocr", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_OCR_MODEL
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

    def extract_text(self, image_bytes: bytes) -> str:
        """从图像中提取文字；无文字时返回空字符串。失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("ocr")
        url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        data = self._client.post_json(
            "/chat/completions",
            {
                "model": self._model,
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
