from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Literal

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError

Capability = Literal["llm", "vision", "speech", "embedding"]
QWEN_ASR_MODEL = re.compile(r"^qwen3-asr-flash(?:-\d{4}-\d{2}-\d{2})?$")


class OpenAICompatibleClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_configured(self, capability: Capability) -> bool:
        return bool(
            self.settings.ai_base_url and self.settings.ai_api_key and self._model(capability)
        )

    def require(self, capability: Capability) -> None:
        if not self.is_configured(capability):
            raise AppError(
                status_code=503,
                code=f"{capability.upper()}_NOT_CONFIGURED",
                message=f"The {capability} provider is not configured for this environment.",
            )

    def chat_text(self, *, system: str, prompt: str) -> str:
        payload = self._chat_payload("llm", system, prompt, [])
        return self._chat_request(payload)

    def chat_json(
        self,
        *,
        capability: Literal["llm", "vision"],
        system: str,
        prompt: str,
        images: list[Path] | None = None,
    ) -> dict[str, Any]:
        payload = self._chat_payload(capability, system, prompt, images or [])
        payload["response_format"] = {"type": "json_object"}
        text = self._chat_request(payload)
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise AppError(
                    status_code=502,
                    code="INVALID_AI_OUTPUT",
                    message="The AI provider did not return valid structured data.",
                ) from error
            try:
                value = json.loads(match.group(0))
            except json.JSONDecodeError as error:
                raise AppError(
                    status_code=502,
                    code="INVALID_AI_OUTPUT",
                    message="The AI provider did not return valid structured data.",
                ) from error
        if not isinstance(value, dict):
            raise AppError(
                status_code=502,
                code="INVALID_AI_OUTPUT",
                message="The AI provider returned an unexpected result shape.",
            )
        return value

    def transcribe(self, audio_path: Path) -> str:
        self.require("speech")
        model = self._model("speech")
        assert model is not None
        if QWEN_ASR_MODEL.fullmatch(model):
            encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
            return self._chat_request(
                {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": f"data:audio/wav;base64,{encoded}"
                                    },
                                }
                            ],
                        }
                    ],
                    "stream": False,
                    "asr_options": {"enable_itn": False},
                }
            )
        with (
            audio_path.open("rb") as source,
            httpx.Client(timeout=self.settings.ai_timeout_seconds) as client,
        ):
            response = client.post(
                f"{self.settings.ai_base_url}/audio/transcriptions",
                headers=self._auth_headers(),
                data={"model": model},
                files={"file": (audio_path.name, source, "audio/wav")},
            )
        self._raise_provider_error(response)
        value = response.json()
        text = value.get("text") if isinstance(value, dict) else None
        if not isinstance(text, str):
            raise AppError(
                status_code=502,
                code="INVALID_SPEECH_OUTPUT",
                message="The speech provider returned an invalid transcript.",
            )
        return text

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.require("embedding")
        with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.ai_base_url}/embeddings",
                headers=self._headers(),
                json={"model": self._model("embedding"), "input": texts},
            )
        self._raise_provider_error(response)
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise AppError(
                status_code=502,
                code="INVALID_EMBEDDING_OUTPUT",
                message="The embedding provider returned an invalid result.",
            )
        result: list[list[float]] = []
        for item in data:
            vector = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(vector, list) or not all(
                isinstance(value, (int, float)) for value in vector
            ):
                raise AppError(
                    status_code=502,
                    code="INVALID_EMBEDDING_OUTPUT",
                    message="The embedding provider returned an invalid vector.",
                )
            result.append([float(value) for value in vector])
        return result

    def _chat_payload(
        self, capability: Literal["llm", "vision"], system: str, prompt: str, images: list[Path]
    ) -> dict[str, Any]:
        self.require(capability)
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            encoded = base64.b64encode(image.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}", "detail": "low"},
                }
            )
        return {
            "model": self._model(capability),
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content if images else prompt},
            ],
        }

    def _chat_request(self, payload: dict[str, Any]) -> str:
        with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.ai_base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        self._raise_provider_error(response)
        value = response.json()
        try:
            content = value["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AppError(
                status_code=502,
                code="INVALID_AI_OUTPUT",
                message="The AI provider returned an invalid response.",
            ) from error
        if not isinstance(content, str):
            raise AppError(
                status_code=502,
                code="INVALID_AI_OUTPUT",
                message="The AI provider returned an invalid response.",
            )
        return content.strip()

    def _headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    def _auth_headers(self) -> dict[str, str]:
        key = self.settings.ai_api_key
        assert key is not None
        return {"Authorization": f"Bearer {key.get_secret_value()}"}

    def _model(self, capability: Capability) -> str | None:
        return {
            "llm": self.settings.llm_model,
            "vision": self.settings.vision_model,
            "speech": self.settings.speech_model,
            "embedding": self.settings.embedding_model,
        }[capability]

    @staticmethod
    def _raise_provider_error(response: httpx.Response) -> None:
        if response.is_success:
            return
        if response.status_code == 429:
            code, message = "AI_RATE_LIMITED", "The AI provider is busy. Retry later."
        elif response.status_code in {401, 403}:
            code, message = "AI_AUTH_FAILED", "The AI provider credentials were rejected."
        else:
            code, message = "AI_PROVIDER_ERROR", "The AI provider request failed."
        raise AppError(status_code=502, code=code, message=message)
