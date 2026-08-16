"""Storage service facade. Selects the provider from configuration."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings

from .base import StorageProvider
from .local import LocalStorageProvider


class StorageService:
    def __init__(self, provider: StorageProvider):
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def save_bytes(self, storage_path: str, data: bytes) -> str:
        return self._provider.save_bytes(storage_path, data)

    def open_bytes(self, storage_path: str) -> bytes:
        return self._provider.open_bytes(storage_path)

    def delete(self, storage_path: str) -> None:
        self._provider.delete(storage_path)

    def exists(self, storage_path: str) -> bool:
        return self._provider.exists(storage_path)


def _build_provider() -> StorageProvider:
    settings = get_settings()
    provider_name = settings.STORAGE_PROVIDER
    if provider_name == "s3" or provider_name == "supabase":
        # S3 / Supabase providers are available when their credentials are configured.
        try:
            from .remote import RemoteStorageProvider  # noqa: PLC0415

            return RemoteStorageProvider(provider_name)
        except Exception:
            pass  # fall back to local below
    return LocalStorageProvider()


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService(_build_provider())
