"""存储抽象（ARCHITECTURE.md §7.5）。

业务模块只依赖 ``StorageService`` 抽象；默认实现为本地文件系统
（``STORAGE_PROVIDER=local``）。M7 补充 S3 兼容对象存储实现
（``STORAGE_PROVIDER=s3`` / ``supabase``，Supabase 走 S3 兼容端点），
boto3 为 optional 依赖（``pip install .[s3]``）。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

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


class S3StorageProvider(StorageService):
    """S3 兼容对象存储（AWS S3 / Supabase Storage S3 端点 / MinIO 等）。

    boto3 为 optional 依赖：未安装且选择 s3/supabase 时给出可读错误。
    测试可通过 ``client`` 参数注入 stub 客户端，无需真实 boto3。
    """

    def __init__(
        self,
        bucket: str | None = None,
        client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.bucket = bucket or settings.S3_BUCKET
        if not self.bucket:
            raise ValueError("S3 存储未配置：请设置 S3_BUCKET")
        if client is not None:
            self.client = client
            return
        try:
            import boto3
        except ImportError as exc:
            raise ValueError(
                "STORAGE_PROVIDER=s3/supabase 需要 boto3，"
                "请执行 `pip install .[s3]`（或 uv pip install '.[s3]'）"
            ) from exc
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION or None,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        )

    def save(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def read(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:  # noqa: BLE001 - botocore ClientError 或无 boto3 时的 stub
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound") or isinstance(exc, FileNotFoundError):
                return False
            # stub 客户端可抛出带 404 语义的普通异常
            if exc.__class__.__name__ == "NotFoundError":
                return False
            raise


def get_storage_service() -> StorageService:
    settings = get_settings()
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    if settings.STORAGE_PROVIDER in ("s3", "supabase"):
        # Supabase 走 S3 兼容端点：将 S3_ENDPOINT_URL 指向 Supabase Storage 的
        # S3 endpoint（见 docs/DEPLOYMENT.md「存储」）
        return S3StorageProvider()
    raise ValueError(f"不支持的存储提供商: {settings.STORAGE_PROVIDER}")
