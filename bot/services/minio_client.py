from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import aioboto3
from botocore.exceptions import ClientError

from config import settings


@dataclass(frozen=True)
class UploadedObject:
    bucket: str
    key: str


class MinioClient:
    def __init__(self) -> None:
        self._session = aioboto3.Session()

    async def upload_file(
        self,
        *,
        chat_id: int,
        data: bytes,
        filename: str,
        content_type: str,
    ) -> UploadedObject:
        bucket = settings.MINIO_BUCKET
        key = f"uploads/{chat_id}/{uuid4()}/{filename}"
        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url(),
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        ) as client:
            await self._ensure_bucket_exists(client, bucket)
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return UploadedObject(bucket=bucket, key=key)

    @staticmethod
    async def _ensure_bucket_exists(client: object, bucket: str) -> None:
        try:
            await client.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            await client.create_bucket(Bucket=bucket)

    @staticmethod
    def _endpoint_url() -> str:
        endpoint = settings.MINIO_ENDPOINT
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return f"http://{endpoint}"


minio_client = MinioClient()
