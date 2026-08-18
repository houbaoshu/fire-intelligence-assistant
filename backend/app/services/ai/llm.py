"""LLM 能力服务（OpenAI 兼容 chat completions）。

职责：推理与文本生成（AI_CONTEXT.md「Large Language Model」）。
不做 OCR、不做向量检索。模型与地址经模型路由解析（providers.py：
DB 生效配置优先，回退环境变量）。
"""

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services.ai.http_client import (
    OpenAICompatClient,
    ai_not_configured,
    ai_service_error,
)
from app.services.ai.providers import resolve_capability_config


class LLMService:
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
            else resolve_capability_config("llm", settings=self._settings, session=session)
        )
        self._model = config.model if config else self._settings.AI_LLM_MODEL
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

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        """执行一次对话补全，返回 assistant 文本；失败抛可读应用异常。"""
        message = self.chat_raw(messages, temperature=temperature)
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ai_service_error("AI 能力 llm 返回了空内容")
        return content

    def chat_raw(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.2,
        tools: list[dict] | None = None,
    ) -> dict:
        """执行一次对话补全，返回原始 assistant message 字典（含 tool_calls）。

        ``tools`` 为 OpenAI 兼容 function calling 的工具定义列表（M8 Agent）。
        失败抛可读应用异常。
        """
        if self._client is None:
            raise ai_not_configured("llm")
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        data = self._client.post_json("/chat/completions", payload)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ai_service_error("AI 能力 llm 返回了无法解析的响应")
        if not isinstance(message, dict):
            raise ai_service_error("AI 能力 llm 返回了无法解析的响应")
        return message
