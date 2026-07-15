from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    name: str = "Fire Intelligence Platform API"
    version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api"
    database_url: str = "sqlite+pysqlite:///./data/fire_intelligence.db"
    storage_backend: Literal["local"] = "local"
    storage_root: Path = Path("data/storage")
    max_video_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    max_audio_bytes: int = Field(default=200 * 1024 * 1024, ge=1)
    max_document_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    max_upload_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    task_workers: int = Field(default=2, ge=1, le=16)
    task_stale_minutes: int = Field(default=30, ge=1, le=1440)
    task_max_attempts: int = Field(default=3, ge=1, le=10)
    ai_base_url: str | None = None
    ai_api_key: SecretStr | None = None
    llm_model: str | None = None
    vision_model: str | None = None
    speech_model: str | None = None
    embedding_model: str | None = None
    ai_timeout_seconds: int = Field(default=120, ge=5, le=600)
    retrieval_limit: int = Field(default=6, ge=1, le=20)
    chunk_size: int = Field(default=900, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    max_video_frames: int = Field(default=6, ge=1, le=20)
    auth_secret_key: SecretStr | None = None
    development_secret_file: Path = Path("data/.auth-secret")
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    refresh_token_days: int = Field(default=7, ge=1, le=90)
    registration_enabled: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @model_validator(mode="after")
    def validate_production_security(self) -> Settings:
        if self.auth_secret_key is not None:
            value = self.auth_secret_key.get_secret_value()
            if not value:
                self.auth_secret_key = None
            elif len(value) < 32:
                raise ValueError("APP_AUTH_SECRET_KEY must contain at least 32 characters")
        if self.environment == "production" and self.auth_secret_key is None:
            raise ValueError("APP_AUTH_SECRET_KEY is required in production")
        if self.ai_base_url:
            self.ai_base_url = self.ai_base_url.rstrip("/")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("APP_CHUNK_OVERLAP must be smaller than APP_CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_auth_secret(settings: Settings) -> bytes:
    if settings.auth_secret_key is not None:
        return settings.auth_secret_key.get_secret_value().encode("utf-8")

    if settings.environment == "production":
        raise RuntimeError("APP_AUTH_SECRET_KEY is required in production")

    path = settings.development_secret_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise RuntimeError(f"Development signing key is invalid: {path}")
        return value.encode("utf-8")

    value = secrets.token_urlsafe(48)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(value)
    return value.encode("utf-8")
