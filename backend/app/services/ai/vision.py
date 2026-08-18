"""Vision 能力服务（OpenAI 兼容多模态 chat completions）。

职责：图像/视频帧理解（AI_CONTEXT.md「Vision Model」）。不做 OCR 推理，
不生成最终文档。模型与地址经模型路由解析（providers.py：DB 生效配置优先，回退环境变量）。
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


class VisionService:
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
            else resolve_capability_config("vision", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_VISION_MODEL
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

    def analyze_image(
        self,
        prompt: str,
        *,
        image_bytes: bytes | None = None,
        image_url: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """分析单张图片，返回模型文本输出（可为 JSON 文本，解析归调用方）。

        图片以 base64 data URL 或外部 URL 提供，二者必居其一。
        失败抛可读应用异常。
        """
        if self._client is None:
            raise ai_not_configured("vision")
        if image_bytes is not None:
            url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
        elif image_url is not None:
            url = image_url
        else:
            raise ValueError("analyze_image 需要 image_bytes 或 image_url")
        data = self._client.post_json(
            "/chat/completions",
            {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                "temperature": temperature,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ai_service_error("AI 能力 vision 返回了无法解析的响应")
        if not isinstance(content, str) or not content.strip():
            raise ai_service_error("AI 能力 vision 返回了空内容")
        return content
