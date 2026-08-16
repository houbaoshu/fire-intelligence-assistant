"""LLM service: reasoning, structured extraction, question answering."""
from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger

from .client import AIProviderClient

logger = get_logger("ai.llm")


class LLMService:
    def __init__(self, client: AIProviderClient | None = None):
        self.client = client or AIProviderClient()

    @property
    def model(self) -> str | None:
        from app.services.aiplatform.router import resolve_model

        return resolve_model("llm")

    def chat(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.client.chat(self.model or "", messages, temperature=temperature)

    def structured(self, system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
        """Ask the LLM for a JSON object; parse and validate it strictly."""
        text = self.client.chat(
            self.model or "", [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            json_mode=True,
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Some providers return fenced json; try to extract the object
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    raise AIProviderError("AI 输出不是合法 JSON") from None
            else:
                raise AIProviderError("AI 输出不是合法 JSON") from None
        if not isinstance(data, dict):
            raise AIProviderError("AI 输出不是 JSON 对象")
        return data
