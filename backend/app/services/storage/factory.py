"""Storage service factory."""

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.storage.base import StorageService

logger = get_logger(__name__)

_storage_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create storage service instance based on configuration.

    Returns:
        StorageService instance (local or Supabase)
    """
    global _storage_instance

    if _storage_instance is not None:
        return _storage_instance

    settings = get_settings()

    if settings.storage_provider == "supabase":
        from app.services.storage.supabase import SupabaseStorageService

        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("Supabase storage configured but URL or key is missing")

        _storage_instance = SupabaseStorageService(
            url=settings.supabase_url,
            key=settings.supabase_key,
            bucket="fire-intelligence",
        )
        logger.info("Using Supabase storage")
    else:
        from app.services.storage.local import LocalStorageService

        _storage_instance = LocalStorageService(base_path=settings.local_storage_path)
        logger.info("Using local storage")

    return _storage_instance
