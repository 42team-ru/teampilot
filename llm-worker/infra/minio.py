import io
from minio import Minio

from settings import settings

_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


def download_file(bucket: str, key: str) -> bytes:
    response = _client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def file_exists(bucket: str, key: str) -> bool:
    try:
        _client.stat_object(bucket, key)
        return True
    except Exception:
        return False


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    _client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )

