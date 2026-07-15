"""OpenAI-compatible LLM service."""

from __future__ import annotations

import json

import openai

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """OpenAI-compatible LLM service for text generation.

    Uses the ``openai`` async client to communicate with any
    OpenAI-compatible endpoint (OpenAI, Qwen, DeepSeek, etc.).
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
        self._model = settings.llm_model

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            messages: List of message dicts with ``role`` and ``content``.
            temperature: Sampling temperature.
            response_format: Optional response format specification.

        Returns:
            Assistant response text.
        """
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        logger.info(
            "LLM chat request", extra={"model": self._model, "message_count": len(messages)}
        )

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return content

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> dict:
        """Send a chat request expecting a JSON response.

        The model is instructed to respond in JSON.  The response is
        parsed and returned as a dict.

        Args:
            messages: List of message dicts.
            temperature: Sampling temperature (lower for more deterministic output).

        Returns:
            Parsed JSON dict.

        Raises:
            AppException: If the response is not valid JSON.
        """
        response_text = await self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response_text)
            if not isinstance(result, dict):
                raise ValueError("Expected JSON object, got " + type(result).__name__)
            return result
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM returned invalid JSON: %s", response_text[:500])
            raise AppException(
                "AI returned invalid JSON response",
                details={"raw_response": response_text[:500]},
            ) from exc
