"""Application configuration.

All settings are read from environment variables (optionally via a .env file).
Secrets must never be hard-coded in source code.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    APP_NAME: str = "Fire Intelligence Platform"
    APP_ENV: str = "development"  # development | testing | production
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Auth
    SECRET_KEY: str = Field(default="dev-secret-change-me", min_length=8)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REGISTRATION_ENABLED: bool = True
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123456"

    # Database
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # Storage
    STORAGE_PROVIDER: str = "local"  # local | s3 | supabase
    STORAGE_LOCAL_ROOT: str = "./data/storage"
    S3_STORAGE_BUCKET: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None
    SUPABASE_STORAGE_BUCKET: str | None = None

    # AI (OpenAI-compatible providers)
    OPENAI_API_KEY: str | None = None
    AI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str | None = None
    VISION_MODEL: str | None = None
    OCR_MODEL: str | None = None
    SPEECH_MODEL: str | None = None
    EMBEDDING_MODEL: str | None = None
    RERANK_MODEL: str | None = None
    RERANK_BASE_URL: str | None = None
    AI_TIMEOUT_SECONDS: float = 120.0

    # RAG
    VECTOR_STORE_PROVIDER: str = "local"  # local | chroma
    RAG_TOP_K: int = 8
    RAG_RERANK_TOP_K: int = 4

    # MCP (Model Context Protocol) servers, JSON list of {name,url,api_key}
    MCP_SERVERS: str | None = None

    # Tasks
    TASK_WORKER_IN_PROCESS: bool = True
    TASK_POLL_INTERVAL_SECONDS: float = 2.0
    TASK_MAX_RETRIES: int = 3
    TASK_BACKOFF_SECONDS: float = 5.0
    TASK_STALE_MINUTES: int = 30

    # Upload limits (MB)
    MAX_VIDEO_SIZE_MB: int = 500
    MAX_AUDIO_SIZE_MB: int = 200
    MAX_DOC_SIZE_MB: int = 50
    MAX_IMAGE_SIZE_MB: int = 20

    @property
    def storage_root(self) -> Path:
        root = Path(self.STORAGE_LOCAL_ROOT)
        if not root.is_absolute():
            root = BASE_DIR / root
        return root

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def templates_dir(self) -> Path:
        return self.data_dir / "templates"

    @property
    def temporary_dir(self) -> Path:
        return self.data_dir / "temporary"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"

    def ensure_directories(self) -> None:
        for d in (self.storage_root, self.data_dir, self.templates_dir, self.temporary_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear the cached settings (used by tests)."""
    get_settings.cache_clear()
    return get_settings()
