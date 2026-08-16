"""Remote object storage (S3-compatible / Supabase Storage).

Used only when STORAGE_PROVIDER=s3 or supabase and credentials are configured.
Kept behind the StorageProvider interface; business code never touches this.
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import StorageError

from .base import StorageProvider


class RemoteStorageProvider(StorageProvider):
    def __init__(self, kind: str):
        settings = get_settings()
        self.name = kind
        if kind == "s3":
            if not (settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY and settings.S3_STORAGE_BUCKET):
                raise StorageError("S3 存储配置不完整")
            try:
                import boto3  # type: ignore  # noqa: PLC0415
            except ImportError:
                raise StorageError("缺少 boto3,无法使用 S3 存储") from None
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            )
            self._bucket = settings.S3_STORAGE_BUCKET
        elif kind == "supabase":
            if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY and settings.SUPABASE_STORAGE_BUCKET):
                raise StorageError("Supabase 存储配置不完整")
            self._client = None
            self._bucket = settings.SUPABASE_STORAGE_BUCKET
        else:  # pragma: no cover
            raise StorageError(f"未知存储提供商: {kind}")

    def save_bytes(self, storage_path: str, data: bytes) -> str:
        if self._client is not None:
            self._client.put_object(Bucket=self._bucket, Key=storage_path, Body=data)
        else:
            import httpx  # noqa: PLC0415

            settings = get_settings()
            url = f"{settings.SUPABASE_URL}/storage/v1/object/{self._bucket}/{storage_path}"
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, content=data, headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"})
                if resp.status_code >= 400:
                    raise StorageError("Supabase 上传失败")
        return storage_path

    def open_bytes(self, storage_path: str) -> bytes:
        if self._client is not None:
            obj = self._client.get_object(Bucket=self._bucket, Key=storage_path)
            return obj["Body"].read()
        import httpx  # noqa: PLC0415

        settings = get_settings()
        url = f"{settings.SUPABASE_URL}/storage/v1/object/{self._bucket}/{storage_path}"
        with httpx.Client(timeout=60) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"})
            if resp.status_code >= 400:
                raise StorageError("Supabase 读取失败")
            return resp.content

    def delete(self, storage_path: str) -> None:
        try:
            if self._client is not None:
                self._client.delete_object(Bucket=self._bucket, Key=storage_path)
            else:
                import httpx  # noqa: PLC0415

                settings = get_settings()
                url = f"{settings.SUPABASE_URL}/storage/v1/object/{self._bucket}/{storage_path}"
                with httpx.Client(timeout=60) as client:
                    client.delete(url, headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}"})
        except Exception:  # best-effort delete
            pass

    def exists(self, storage_path: str) -> bool:
        if self._client is not None:
            try:
                self._client.head_object(Bucket=self._bucket, Key=storage_path)
                return True
            except Exception:
                return False
        try:
            self.open_bytes(storage_path)
            return True
        except StorageError:
            return False
