import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from backend.app.config.settings import settings
from backend.app.core.logging import logger


class StorageService(ABC):
    @abstractmethod
    def save_file(self, source_path: str, destination_rel_path: str) -> str:
        """Saves a local file into storage and returns a relative or public URL/path."""
        pass

    @abstractmethod
    def save_bytes(self, data: bytes, destination_rel_path: str) -> str:
        """Saves raw bytes into storage and returns a relative or public URL/path."""
        pass

    @abstractmethod
    def get_file_url(self, rel_path: str) -> str:
        """Returns the accessible download/view URL for an asset."""
        pass

    @abstractmethod
    def get_local_path(self, rel_path: str) -> str:
        """Returns a guaranteed local file path for reading or rendering."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_PATH):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, source_path: str, destination_rel_path: str) -> str:
        src = Path(source_path).resolve()
        target = (self.base_dir / destination_rel_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if src != target:
            shutil.copy2(src, target)
        logger.info(f"Saved file locally to {target}")
        return self.get_file_url(destination_rel_path)

    def save_bytes(self, data: bytes, destination_rel_path: str) -> str:
        target = (self.base_dir / destination_rel_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        logger.info(f"Saved {len(data)} bytes to {target}")
        return self.get_file_url(destination_rel_path)

    def get_file_url(self, rel_path: str) -> str:
        # Standardized download route served by FastAPI static or streaming endpoint
        norm_path = rel_path.replace("\\", "/").lstrip("/")
        return f"/api/v1/storage/{norm_path}"

    def get_local_path(self, rel_path: str) -> str:
        target = (self.base_dir / rel_path).resolve()
        return str(target)


class S3StorageService(StorageService):
    def __init__(self):
        import boto3
        from botocore.client import Config

        self.endpoint = settings.S3_ENDPOINT_URL
        self.bucket = settings.S3_BUCKET_NAME
        self.local_cache = Path(settings.LOCAL_STORAGE_PATH).resolve()

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name=settings.S3_REGION,
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
            except Exception as e:
                logger.warning(f"Failed to create bucket {self.bucket}: {e}")

    def save_file(self, source_path: str, destination_rel_path: str) -> str:
        norm_key = destination_rel_path.replace("\\", "/").lstrip("/")
        self.s3_client.upload_file(source_path, self.bucket, norm_key)
        return self.get_file_url(norm_key)

    def save_bytes(self, data: bytes, destination_rel_path: str) -> str:
        norm_key = destination_rel_path.replace("\\", "/").lstrip("/")
        self.s3_client.put_object(Bucket=self.bucket, Key=norm_key, Body=data)
        return self.get_file_url(norm_key)

    def get_file_url(self, rel_path: str) -> str:
        norm_key = rel_path.replace("\\", "/").lstrip("/")
        if self.endpoint:
            return f"{self.endpoint}/{self.bucket}/{norm_key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{norm_key}"

    def get_local_path(self, rel_path: str) -> str:
        norm_key = rel_path.replace("\\", "/").lstrip("/")
        local_target = (self.local_cache / norm_key).resolve()
        local_target.parent.mkdir(parents=True, exist_ok=True)
        if not local_target.exists():
            self.s3_client.download_file(self.bucket, norm_key, str(local_target))
        return str(local_target)


_storage_instance: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND == "s3" or settings.STORAGE_BACKEND == "minio":
            try:
                _storage_instance = S3StorageService()
                logger.info("Initialized S3/MinIO storage service")
            except Exception as e:
                logger.warning(f"Could not initialize S3 storage ({e}), falling back to LocalStorageService")
                _storage_instance = LocalStorageService()
        else:
            _storage_instance = LocalStorageService()
    return _storage_instance
