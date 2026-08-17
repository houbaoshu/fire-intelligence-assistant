"""AI 能力配置探测。

能力（capability）取值：``llm`` / ``vision`` / ``ocr`` / ``speech`` /
``embedding`` / ``reranker``。
配置一律来自 ``get_settings()``（环境变量），禁止硬编码模型名与密钥。
真实 client 见同目录 ``llm.py`` / ``embedding.py`` / ``reranker.py``
（OpenAI 兼容 HTTP API）；vision/ocr/speech client 由 M4 补充。
"""

from functools import lru_cache

from app.core.config import Settings, get_settings

CAPABILITIES = ("llm", "vision", "ocr", "speech", "embedding", "reranker")


class AIProviders:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self, capability: str) -> bool:
        s = self._settings
        if capability == "llm":
            return bool(s.AI_LLM_API_KEY and s.AI_LLM_MODEL and s.AI_LLM_BASE_URL)
        if capability == "vision":
            return bool(s.AI_VISION_API_KEY and s.AI_VISION_MODEL)
        if capability == "ocr":
            return bool(s.AI_OCR_API_KEY)
        if capability == "speech":
            return bool(s.AI_SPEECH_API_KEY and s.AI_SPEECH_MODEL)
        if capability == "embedding":
            return bool(
                s.AI_EMBEDDING_API_KEY and s.AI_EMBEDDING_MODEL and s.AI_EMBEDDING_BASE_URL
            )
        if capability == "reranker":
            return bool(
                s.AI_RERANKER_API_KEY and s.AI_RERANKER_MODEL and s.AI_RERANKER_BASE_URL
            )
        raise ValueError(f"未知 AI 能力: {capability}")

    def missing(self, capabilities: tuple[str, ...]) -> list[str]:
        return [c for c in capabilities if not self.is_configured(c)]


@lru_cache
def get_ai_providers() -> AIProviders:
    return AIProviders()
