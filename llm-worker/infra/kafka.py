from confluent_kafka import Consumer, Producer
from loguru import logger
from pydantic import BaseModel

from settings import settings

_producer = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})


class BatchConsumer:
    def __init__(self, topic: str, group_id: str | None = None) -> None:
        resolved_group_id = group_id or settings.KAFKA_GROUP_ID
        self._consumer = Consumer({
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": resolved_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._consumer.subscribe([topic])
        logger.info(f"Kafka consumer subscribed to {topic!r} group_id={resolved_group_id!r}")

    def poll(self, timeout: float = 1.0):
        msg = self._consumer.poll(timeout=timeout)
        if msg is None:
            return None
        if msg.error():
            logger.error(f"Kafka error: {msg.error()}")
            return None
        return msg

    def commit(self, msg) -> None:
        self._consumer.commit(message=msg)

    def close(self) -> None:
        self._consumer.close()


def publish(topic: str, event: BaseModel, key: str) -> None:
    try:
        _producer.produce(topic, value=event.model_dump_json().encode(), key=key.encode())
        _producer.poll(0)
    except Exception as e:
        logger.error(f"Failed to publish to {topic!r}: {e}")


def flush() -> None:
    _producer.flush()
