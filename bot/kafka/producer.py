import asyncio
import time
from threading import Lock

from confluent_kafka import Producer
from loguru import logger
from pydantic import BaseModel

from config import settings


class EventProducer:
    def __init__(self, bootstrap_servers: str) -> None:
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})
        self._lock = Lock()

    async def publish(self, topic: str, event: BaseModel, key: str | None = None) -> None:
        payload = event.model_dump_json().encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None
        started = time.perf_counter()
        try:
            await asyncio.to_thread(self._publish_sync, topic, payload, key_bytes)
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return

        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms >= settings.KAFKA_SLOW_PUBLISH_MS:
            logger.warning(
                "Slow Kafka publish: topic={} elapsed_ms={:.1f}",
                topic,
                elapsed_ms,
            )

    def _publish_sync(self, topic: str, payload: bytes, key: bytes | None) -> None:
        with self._lock:
            self._producer.produce(topic, value=payload, key=key)
            self._producer.poll(0)

    def flush(self) -> None:
        with self._lock:
            self._producer.flush()
