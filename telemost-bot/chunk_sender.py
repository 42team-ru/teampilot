from __future__ import annotations

import io
import json

from confluent_kafka import Producer
from loguru import logger
from minio import Minio

from config import settings

_minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)

_producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})

_TOPIC = "meetings.audio.chunks"


def _ensure_bucket(bucket: str) -> None:
    try:
        if not _minio_client.bucket_exists(bucket):
            _minio_client.make_bucket(bucket)
    except Exception as e:
        logger.warning("Could not ensure bucket {!r}: {}", bucket, e)


def _upload(bucket: str, key: str, data: bytes, content_type: str) -> None:
    _ensure_bucket(bucket)
    _minio_client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )


def _publish(topic: str, payload: dict, key: str) -> None:
    _producer.produce(
        topic,
        value=json.dumps(payload).encode("utf-8"),
        key=key.encode("utf-8"),
    )
    _producer.poll(0)


async def send_chunk(
    meeting_id: str,
    team_id: str,
    chunk_index: int,
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    original_filename: str | None = None,
    final_chunk: bool = False,
) -> None:
    """Upload audio chunk to MinIO and publish MeetingAudioChunkEvent to Kafka."""
    if original_filename is None:
        original_filename = f"chunk-{chunk_index:06d}.wav"

    bucket = settings.MINIO_BUCKET
    s3_key = f"meetings/{meeting_id}/chunks/{chunk_index:06d}-{original_filename}"

    if audio_bytes:
        try:
            _upload(bucket, s3_key, audio_bytes, content_type)
            logger.debug(
                "MinIO upload: meeting_id={} chunk={} size={} key={}",
                meeting_id, chunk_index, len(audio_bytes), s3_key,
            )
        except Exception as e:
            logger.error(
                "MinIO upload failed: meeting_id={} chunk={}: {}",
                meeting_id, chunk_index, e,
            )
            raise

    event = {
        "meetingId": meeting_id,
        "teamId": team_id,
        "recorderTelegramId": None,
        "chunkIndex": chunk_index,
        "finalChunk": final_chunk,
        "bucket": bucket,
        "s3Key": s3_key,
        "originalFilename": original_filename,
        "contentType": content_type,
        "team": [],
        "columns": [],
        "stickers": [],
    }

    try:
        _publish(_TOPIC, event, key=meeting_id)
        logger.debug(
            "Kafka published: topic={} meeting_id={} chunk={} final={}",
            _TOPIC, meeting_id, chunk_index, final_chunk,
        )
    except Exception as e:
        logger.error(
            "Kafka publish failed: meeting_id={} chunk={}: {}",
            meeting_id, chunk_index, e,
        )
        raise
