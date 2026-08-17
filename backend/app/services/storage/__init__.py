"""存储抽象（ARCHITECTURE.md §7.5）。

业务模块只依赖 ``StorageService`` 抽象；默认实现为本地文件系统
（``STORAGE_PROVIDER=local``），Supabase / S3 实现按相同接口在后续 milestone 补充。
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class StorageService(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """保存文件并返回存储路径。"""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """按存储路径读取文件内容。"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除存储对象。"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """判断存储对象是否存在。"""


class LocalStorageProvider(StorageService):
    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self.base_dir = Path(base_dir or settings.STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # 防止路径穿越：解析后的路径必须位于 base_dir 之内
        path = (self.base_dir / key).resolve()
        if self.base_dir not in path.parents and path != self.base_dir:
            raise ValueError(f"非法存储路径: {key}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()


def get_storage_service() -> StorageService:
    settings = get_settings()
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    raise ValueError(f"不支持的存储提供商: {settings.STORAGE_PROVIDER}")
