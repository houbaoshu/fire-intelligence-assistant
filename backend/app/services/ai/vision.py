"""Vision model service for image and video analysis."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import openai

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


class VisionService:
    """Vision model service for analysing images and video frames.

    Uses the OpenAI-compatible vision API to understand image content.
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
        self._model = settings.vision_model

    def _encode_image(self, image_path: str) -> str:
        """Read and base64-encode an image file.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            Base64-encoded string.
        """
        data = Path(image_path).read_bytes()
        return base64.b64encode(data).decode("utf-8")

    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyse a single image with the vision model.

        Args:
            image_path: Path to the image file.
            prompt: Text prompt describing what to analyse.

        Returns:
            Vision model text response.
        """
        b64_image = self._encode_image(image_path)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                        },
                    },
                ],
            }
        ]

        logger.info("Vision analysis request", extra={"model": self._model, "image": image_path})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    async def analyze_image_structured(self, image_path: str, prompt: str) -> dict:
        """Analyse an image and return structured JSON.

        The prompt is augmented with an instruction to respond in JSON.

        Args:
            image_path: Path to the image file.
            prompt: Text prompt describing what to analyse.

        Returns:
            Parsed JSON dict.
        """
        structured_prompt = (
            f"{prompt}\n\n"
            "Please respond with a valid JSON object. Do not include any text outside the JSON."
        )
        response_text = await self.analyze_image(image_path, structured_prompt)

        # Try to extract JSON from the response
        try:
            result = json.loads(response_text)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to find JSON block in the response
        import re

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error("Vision model returned non-JSON response: %s", response_text[:500])
        raise AppException(
            "Vision model returned invalid JSON response",
            details={"raw_response": response_text[:500]},
        )
