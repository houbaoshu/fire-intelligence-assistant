"""Supabase storage implementation for production."""

import httpx

from app.core.logging import get_logger
from app.services.storage.base import StorageService

logger = get_logger(__name__)


class SupabaseStorageService(StorageService):
    """Supabase object storage for production deployments."""

    def __init__(self, url: str, key: str, bucket: str):
        """Initialize Supabase storage.

        Args:
            url: Supabase project URL
            key: Supabase API key
            bucket: Storage bucket name
        """
        self.url = url.rstrip("/")
        self.key = key
        self.bucket = bucket
        self.storage_url = f"{self.url}/storage/v1/object/{bucket}"
        logger.info(f"Supabase storage initialized for bucket {bucket}")

    async def upload(self, file_data: bytes, path: str, content_type: str | None = None) -> str:
        """Upload file to Supabase storage.

        Args:
            file_data: Raw file bytes
            path: Object path within bucket
            content_type: MIME type

        Returns:
            Storage path

        Raises:
            httpx.HTTPStatusError: If upload fails
        """
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type or "application/octet-stream",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.storage_url}/{path}",
                headers=headers,
                content=file_data,
                timeout=60.0,
            )
            response.raise_for_status()

        logger.info(f"File uploaded to Supabase: {path}")
        return path

    async def download(self, path: str) -> bytes:
        """Download file from Supabase storage.

        Args:
            path: Object path within bucket

        Returns:
            File bytes

        Raises:
            httpx.HTTPStatusError: If download fails
        """
        headers = {
            "Authorization": f"Bearer {self.key}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.storage_url}/{path}",
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content

    async def delete(self, path: str) -> None:
        """Delete file from Supabase storage.

        Args:
            path: Object path within bucket

        Raises:
            httpx.HTTPStatusError: If deletion fails
        """
        headers = {
            "Authorization": f"Bearer {self.key}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.storage_url}/{path}",
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()

        logger.info(f"File deleted from Supabase: {path}")

    async def get_url(self, path: str) -> str:
        """Get public URL for stored file.

        Args:
            path: Object path within bucket

        Returns:
            Public URL
        """
        return f"{self.storage_url}/{path}"
