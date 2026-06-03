import uuid

from loguru import logger
from pydantic import ValidationError

from infra.kafka import BatchConsumer, flush, publish
from infra.qdrant import is_task_duplicate, store_batch, store_task
from llm.chains import classifier_chain, status_chain, task_chain
from models import (
    ClassificationResult,
    MessageBatchEvent,
    StatusChangeEvent,
    StatusExtraction,
    TaskCreateEvent,
    TaskExtraction,
)
from settings import settings

TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"


def format_messages(batch: MessageBatchEvent) -> str:
    return "\n".join(
        f"[{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def process_batch(batch: MessageBatchEvent) -> None:
    text = format_messages(batch)
    store_batch(batch.event_id, text, batch.chat_id)

    try:
        clf = ClassificationResult.model_validate(
            classifier_chain.invoke({"messages": text})
        )
    except (ValidationError, Exception) as e:
        logger.error(f"Classifier failed (batch={batch.event_id}): {e}")
        return

    logger.debug(f"batch={batch.event_id} {clf}")

    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        _handle_task(batch, text)

    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        _handle_status(batch, text)


def _handle_task(batch: MessageBatchEvent, text: str) -> None:
    try:
        extraction = TaskExtraction.model_validate(
            task_chain.invoke({"messages": text})
        )
    except (ValidationError, Exception) as e:
        logger.error(f"Task chain failed: {e}")
        return

    if is_task_duplicate(extraction.title, extraction.description or ""):
        logger.info(f"Duplicate skipped: {extraction.title!r}")
        return

    task_id = str(uuid.uuid4())
    store_task(task_id, extraction.title, extraction.description or "")

    publish(TOPIC_TASKS, TaskCreateEvent(
        chat_id=batch.chat_id,
        source_batch_id=batch.event_id,
        **extraction.model_dump(),
    ), key=str(batch.chat_id))
    logger.info(f"Task published: {extraction.title!r} chat={batch.chat_id}")


def _handle_status(batch: MessageBatchEvent, text: str) -> None:
    try:
        extraction = StatusExtraction.model_validate(
            status_chain.invoke({"messages": text})
        )
    except (ValidationError, Exception) as e:
        logger.error(f"Status chain failed: {e}")
        return

    publish(TOPIC_STATUS, StatusChangeEvent(
        chat_id=batch.chat_id,
        source_batch_id=batch.event_id,
        **extraction.model_dump(),
    ), key=str(batch.chat_id))
    logger.info(f"Status published: {extraction.action} chat={batch.chat_id}")


def main() -> None:
    logger.info("LLM Worker starting...")

    consumer = BatchConsumer(TOPIC_IN)
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                batch = MessageBatchEvent.model_validate_json(msg.value())
                logger.info(f"Batch {batch.event_id}: {len(batch.messages)} msgs chat={batch.chat_id}")
                process_batch(batch)
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
            finally:
                consumer.commit(msg)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        consumer.close()
        flush()


if __name__ == "__main__":
    main()
