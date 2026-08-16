"""Storage provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    name: str = "base"

    @abstractmethod
    def save_bytes(self, storage_path: str, data: bytes) -> str:
        """Persist bytes at the given logical path; returns the canonical path."""

    @abstractmethod
    def open_bytes(self, storage_path: str) -> bytes:
        """Read the full content of the object at the given path."""

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        """Remove the object (best-effort)."""

    @abstractmethod
    def exists(self, storage_path: str) -> bool:
        """Check whether the object exists."""
