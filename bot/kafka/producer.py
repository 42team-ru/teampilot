from confluent_kafka import Producer
from loguru import logger
from pydantic import BaseModel


class EventProducer:
    def __init__(self, bootstrap_servers: str) -> None:
        self._producer = Producer({"bootstrap.servers": bootstrap_servers})

    async def publish(self, topic: str, event: BaseModel, key: str | None = None) -> None:
        payload = event.model_dump_json().encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None
        try:
            self._producer.produce(topic, value=payload, key=key_bytes)
            self._producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")

    def flush(self) -> None:
        self._producer.flush()
