"""Local filesystem storage provider (development / self-hosted)."""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import StorageError

from .base import StorageProvider


class LocalStorageProvider(StorageProvider):
    name = "local"

    def __init__(self, root: Path | None = None):
        self.root = (root or get_settings().storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_path: str) -> Path:
        # Prevent path traversal: only allow paths inside root
        target = (self.root / storage_path).resolve()
        if not str(target).startswith(str(self.root)):
            raise StorageError("非法存储路径")
        return target

    def save_bytes(self, storage_path: str, data: bytes) -> str:
        target = self._resolve(storage_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(data)
        except OSError as e:
            raise StorageError(f"写入存储失败: {e}") from e
        return storage_path

    def open_bytes(self, storage_path: str) -> bytes:
        target = self._resolve(storage_path)
        if not target.exists():
            raise StorageError("存储对象不存在")
        return target.read_bytes()

    def delete(self, storage_path: str) -> None:
        target = self._resolve(storage_path)
        if target.exists():
            target.unlink()

    def exists(self, storage_path: str) -> bool:
        return self._resolve(storage_path).exists()
