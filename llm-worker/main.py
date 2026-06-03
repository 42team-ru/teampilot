import uuid
from typing import List, Optional, Union

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

# Kafka Topic Constants
TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"


def format_messages(batch: MessageBatchEvent) -> str:
    """
    Formats a batch of messages into a single string for LLM consumption.
    
    Args:
        batch: The message batch event containing individual messages.
        
    Returns:
        A formatted string with timestamps and usernames.
    """
    return "\n".join(
        f"[{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def process_batch(batch: MessageBatchEvent) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    """
    Core logic for processing a message batch.
    
    This function:
    1. Formats messages.
    2. Stores the batch in Qdrant for context/RAG.
    3. Runs a cheap classifier to detect tasks or status changes.
    4. If detected, runs expensive extraction chains.
    5. Returns a list of generated events.
    
    Args:
        batch: The input message batch from Kafka or direct call.
        
    Returns:
        A list of events (TaskCreateEvent or StatusChangeEvent) to be published or processed.
    """
    text = format_messages(batch)
    
    # Store in Qdrant for future RAG context
    # Note: store_batch is currently a placeholder in infra/qdrant.py
    store_batch(batch.event_id, text, batch.chat_id)

    results = []

    try:
        # Step 1: Classification (Cheap LLM)
        clf_output = classifier_chain.invoke({"messages": text})
        clf = ClassificationResult.model_validate(clf_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Classifier failed (batch={batch.event_id}): {e}")
        return results

    logger.debug(f"Classification for batch {batch.event_id}: {clf}")

    # Step 2: Task Extraction (Expensive LLM)
    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        task_event = _extract_task(batch, text)
        if task_event:
            results.append(task_event)

    # Step 3: Status Change Extraction (Expensive LLM)
    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        status_event = _extract_status(batch, text)
        if status_event:
            results.append(status_event)

    return results


def _extract_task(batch: MessageBatchEvent, text: str) -> Optional[TaskCreateEvent]:
    """
    Extracts task details from text and performs deduplication.
    """
    try:
        extraction_output = task_chain.invoke({"messages": text})
        extraction = TaskExtraction.model_validate(extraction_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Task extraction chain failed: {e}")
        return None

    # Deduplication check via Qdrant
    if is_task_duplicate(extraction.title, extraction.description or ""):
        logger.info(f"Duplicate task detected and skipped: {extraction.title!r}")
        return None

    task_id = str(uuid.uuid4())
    store_task(task_id, extraction.title, extraction.description or "")

    return TaskCreateEvent(
        chat_id=batch.chat_id,
        source_batch_id=batch.event_id,
        **extraction.model_dump(),
    )


def _extract_status(batch: MessageBatchEvent, text: str) -> Optional[StatusChangeEvent]:
    """
    Extracts status change details from text.
    """
    try:
        extraction_output = status_chain.invoke({"messages": text})
        extraction = StatusExtraction.model_validate(extraction_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Status extraction chain failed: {e}")
        return None

    return StatusChangeEvent(
        chat_id=batch.chat_id,
        source_batch_id=batch.event_id,
        **extraction.model_dump(),
    )


def main() -> None:
    """
    Kafka Consumer loop entry point.
    """
    logger.info("LLM Worker starting in Kafka Consumer mode...")

    consumer = BatchConsumer(TOPIC_IN)
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
                
            try:
                # Parse incoming batch
                batch = MessageBatchEvent.model_validate_json(msg.value())
                logger.info(f"Processing batch {batch.event_id} ({len(batch.messages)} msgs) from chat {batch.chat_id}")
                
                # Process the batch and get results
                events = process_batch(batch)
                
                # Publish results to respective Kafka topics
                for event in events:
                    if isinstance(event, TaskCreateEvent):
                        publish(TOPIC_TASKS, event, key=str(batch.chat_id))
                        logger.info(f"Task event published: {event.title!r}")
                    elif isinstance(event, StatusChangeEvent):
                        publish(TOPIC_STATUS, event, key=str(batch.chat_id))
                        logger.info(f"Status event published: {event.action}")
                        
            except Exception as e:
                logger.error(f"Error processing message from Kafka: {e}")
            finally:
                consumer.commit(msg)
                
    except KeyboardInterrupt:
        logger.info("Graceful shutdown initiated...")
    finally:
        consumer.close()
        flush()


if __name__ == "__main__":
    main()
