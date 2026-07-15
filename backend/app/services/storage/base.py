"""Abstract base class for storage services."""

from abc import ABC, abstractmethod


class StorageService(ABC):
    """Abstract interface for object storage operations."""

    @abstractmethod
    async def upload(self, file_data: bytes, path: str, content_type: str | None = None) -> str:
        """Upload file data to storage.

        Args:
            file_data: Raw file bytes
            path: Storage path/key
            content_type: Optional MIME type

        Returns:
            Storage path or URL
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file from storage.

        Args:
            path: Storage path/key

        Returns:
            File bytes
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file from storage.

        Args:
            path: Storage path/key
        """
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Get accessible URL for stored file.

        Args:
            path: Storage path/key

        Returns:
            Accessible URL
        """
        pass
