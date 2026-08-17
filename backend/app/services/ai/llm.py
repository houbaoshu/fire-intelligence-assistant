"""LLM 能力服务（OpenAI 兼容 chat completions）。

职责：推理与文本生成（AI_CONTEXT.md「Large Language Model」）。
不做 OCR、不做向量检索。模型与地址一律来自环境变量配置。
"""

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import AIProviders


class LLMService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: OpenAICompatClient | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or (
            OpenAICompatClient(
                base_url=self._settings.AI_LLM_BASE_URL,
                api_key=self._settings.AI_LLM_API_KEY,
                settings=self._settings,
                transport=transport,
            )
            if AIProviders(self._settings).is_configured("llm")
            else None
        )

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        """执行一次对话补全，返回 assistant 文本；失败抛可读应用异常。"""
        if self._client is None:
            raise ai_not_configured("llm")
        data = self._client.post_json(
            "/chat/completions",
            {
                "model": self._settings.AI_LLM_MODEL,
                "messages": messages,
                "temperature": temperature,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ai_service_error("AI 能力 llm 返回了无法解析的响应")
        if not isinstance(content, str) or not content.strip():
            raise ai_service_error("AI 能力 llm 返回了空内容")
        return content
