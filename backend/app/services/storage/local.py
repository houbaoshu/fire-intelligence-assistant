"""Local filesystem storage implementation for development."""

import os
from pathlib import Path

import aiofiles

from app.core.logging import get_logger
from app.services.storage.base import StorageService

logger = get_logger(__name__)


class LocalStorageService(StorageService):
    """Local filesystem storage for development and testing."""

    def __init__(self, base_path: str):
        """Initialize local storage.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at {self.base_path}")

    async def upload(self, file_data: bytes, path: str, content_type: str | None = None) -> str:
        """Upload file to local filesystem.

        Args:
            file_data: Raw file bytes
            path: Relative path within base directory
            content_type: Ignored for local storage

        Returns:
            Storage path
        """
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_data)

        logger.info(f"File uploaded to {full_path}")
        return path

    async def download(self, path: str) -> bytes:
        """Download file from local filesystem.

        Args:
            path: Relative path within base directory

        Returns:
            File bytes

        Raises:
            FileNotFoundError: If file does not exist
        """
        full_path = self.base_path / path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        """Delete file from local filesystem.

        Args:
            path: Relative path within base directory
        """
        full_path = self.base_path / path

        if full_path.exists():
            os.remove(full_path)
            logger.info(f"File deleted: {full_path}")

    async def get_url(self, path: str) -> str:
        """Get file URL (local path for development).

        Args:
            path: Relative path within base directory

        Returns:
            Absolute file path
        """
        return str(self.base_path / path)
