"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Fire Intelligence Platform.

    Values are read from environment variables and/or a ``.env`` file
    located in the backend project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fire_intelligence"

    # ── Security / JWT ──────────────────────────────────────────────────
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # ── Object Storage ──────────────────────────────────────────────────
    storage_provider: str = "local"  # "local" | "supabase"
    local_storage_path: str = "./data/storage"
    supabase_url: str = ""
    supabase_key: str = ""

    # ── AI / LLM ────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_base_url: str = ""
    llm_model: str = "qwen-plus"
    vision_model: str = "qwen-vl-plus"
    embedding_model: str = "text-embedding-v3"
    reranker_model: str = "gte-rerank"

    # ── RAG / Chroma ────────────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "fire_knowledge"

    # ── CORS ────────────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # ── Logging ─────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── File Uploads ────────────────────────────────────────────────────
    max_upload_size_mb: int = 500

    # ── Validators ──────────────────────────────────────────────────────

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> list[str]:
        """Accept either a JSON array string or a comma-separated list."""
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed]
            except (json.JSONDecodeError, TypeError):
                pass
            # Fall back to comma-separated
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v]
        return cls.model_fields["cors_origins"].default or []

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    The instance is created once and reused for the lifetime of the
    process, ensuring consistent configuration across the application.
    """
    return Settings()
