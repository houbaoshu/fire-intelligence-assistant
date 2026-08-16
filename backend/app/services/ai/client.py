"""Minimal OpenAI-compatible client built on httpx.

Model names and base URLs always come from configuration; nothing is hard-coded.
Supports injecting a custom httpx.Client transport for tests.
"""
from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import AINotConfiguredError, AIProviderError
from app.core.logging import get_logger

logger = get_logger("ai.client")


class AIProviderClient:
    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self.settings = get_settings()
        if not self.settings.OPENAI_API_KEY:
            raise AINotConfiguredError("AI 服务未配置:请设置 OPENAI_API_KEY 与模型环境变量")
        self.base_url = (self.settings.AI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.api_key = self.settings.OPENAI_API_KEY
        self.timeout = self.settings.AI_TIMEOUT_SECONDS
        self._transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
            transport=self._transport,
        )

    @staticmethod
    def _check(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            body = resp.text[:500]
            logger.warning("AI provider error %s: %s", resp.status_code, body)
            raise AIProviderError(f"AI 服务返回错误({resp.status_code})")

    def chat(self, model: str, messages: list[dict], *, temperature: float = 0.2, json_mode: bool = False, max_tokens: int | None = None) -> str:
        """Chat completion; returns the assistant text content."""
        if not model:
            raise AINotConfiguredError("未配置 LLM 模型")
        payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        with self._client() as c:
            resp = c.post("/chat/completions", json=payload)
            self._check(resp)
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise AIProviderError("AI 响应格式异常") from None

    def chat_vision(self, model: str, prompt: str, image_bytes: bytes, image_mime: str = "image/jpeg") -> str:
        """Chat completion with a single inline image (vision)."""
        if not model:
            raise AINotConfiguredError("未配置视觉模型")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64}"}},
                ],
            }
        ]
        return self.chat(model, messages)

    def embeddings(self, model: str, texts: list[str]) -> list[list[float]]:
        if not model:
            raise AINotConfiguredError("未配置 Embedding 模型")
        with self._client() as c:
            resp = c.post("/embeddings", json={"model": model, "input": texts})
            self._check(resp)
            data = resp.json()
        try:
            ordered = sorted(data["data"], key=lambda d: d["index"])
            return [item["embedding"] for item in ordered]
        except (KeyError, TypeError):
            raise AIProviderError("Embedding 响应格式异常") from None

    def audio_transcription(self, model: str, audio_bytes: bytes, filename: str) -> str:
        if not model:
            raise AINotConfiguredError("未配置语音识别模型")
        with httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
            transport=self._transport,
        ) as c:
            files = {"file": (filename, audio_bytes)}
            data = {"model": model}
            resp = c.post("/audio/transcriptions", files=files, data=data)
            self._check(resp)
            payload = resp.json()
        text = payload.get("text", "") if isinstance(payload, dict) else str(payload)
        return text or ""

    def rerank(self, model: str, query: str, documents: list[str], top_n: int | None = None) -> list[float]:
        """Rerank using a rerank-compatible endpoint (e.g. Cohere-style)."""
        if not model:
            raise AINotConfiguredError("未配置 Rerank 模型")
        base = (self.settings.RERANK_BASE_URL or self.base_url).rstrip("/")
        with httpx.Client(
            base_url=base,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=self.timeout,
            transport=self._transport,
        ) as c:
            payload: dict[str, Any] = {"model": model, "query": query, "documents": documents}
            if top_n:
                payload["top_n"] = top_n
            resp = c.post("/rerank", json=payload)
            self._check(resp)
            data = resp.json()
        try:
            results = data["results"]
            scores = [0.0] * len(documents)
            for r in results:
                idx = r.get("index")
                if isinstance(idx, int) and 0 <= idx < len(documents):
                    scores[idx] = float(r.get("relevance_score", 0.0))
            return scores
        except (KeyError, TypeError):
            raise AIProviderError("Rerank 响应格式异常") from None
