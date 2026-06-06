import time
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from loguru import logger

from infra.kafka import BatchConsumer, flush, publish
from infra.qdrant import delete_task, init_collections, store_task
from models import (
    MessageBatchEvent,
    StatusChangeEvent,
    TaskCreateEvent,
    TaskLifecycleEvent,
    TranscriptReadyEvent,
    proto_to_batch_event,
)
from processor import process_batch, process_transcript
from proto_generated.ru.team42.events import message_batch_pb2
from settings import settings

TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"
TOPIC_TRANSCRIPT = "audio.transcript.ready"
TOPIC_LIFECYCLE = "tasks.lifecycle"


def _process_and_publish_batch(batch: MessageBatchEvent) -> None:
    events = process_batch(batch)
    tasks_published = 0
    statuses_published = 0
    for event in events:
        if isinstance(event, TaskCreateEvent):
            publish(TOPIC_TASKS, event, key=str(batch.team_id))
            tasks_published += 1
        elif isinstance(event, StatusChangeEvent):
            publish(TOPIC_STATUS, event, key=str(batch.team_id))
            statuses_published += 1
    logger.info(
        f"[BATCH {batch.event_id[:8]}] msgs={len(batch.messages)} "
        f"→ tasks={tasks_published} statuses={statuses_published}"
    )


def run_lifecycle_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_LIFECYCLE)
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                event = TaskLifecycleEvent.model_validate_json(msg.value().decode())
                if event.type in ("CONFIRMED", "UPDATED"):
                    store_task(event.task_id, event.title, event.description or "", event.team_id)
                    logger.info(f"Stored/updated task {event.task_id!r} in Qdrant")
                elif event.type == "CANCELLED":
                    delete_task(event.task_id)
            except Exception as e:
                logger.error(f"Error processing lifecycle event: {e}")
            finally:
                consumer.commit(msg)
    finally:
        consumer.close()


def run_transcript_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_TRANSCRIPT)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="llm-transcript") as executor:
        try:
            while not stop_event.is_set():
                while pending and pending[0][0].done():
                    fut, msg = pending.popleft()
                    if fut.exception():
                        logger.error(f"Transcript processing failed: {fut.exception()}")
                    consumer.commit(msg)

                if len(pending) >= concurrency:
                    time.sleep(0.05)
                    continue

                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                try:
                    event = TranscriptReadyEvent.model_validate_json(msg.value().decode())
                    fut = executor.submit(process_transcript, event)
                    pending.append((fut, msg))
                except Exception as e:
                    logger.error(f"Error parsing transcript event: {e}")
                    consumer.commit(msg)
        finally:
            for fut, msg in pending:
                try:
                    fut.result(timeout=120)
                except Exception as e:
                    logger.error(f"Pending transcript failed at shutdown: {e}")
                consumer.commit(msg)
            consumer.close()


def main() -> None:
    logger.info("LLM Worker starting in Kafka Consumer mode...")
    init_collections()

    stop_event = threading.Event()
    transcript_thread = threading.Thread(
        target=run_transcript_consumer,
        args=(stop_event,),
        daemon=True,
        name="transcript-consumer",
    )
    transcript_thread.start()

    lifecycle_thread = threading.Thread(
        target=run_lifecycle_consumer,
        args=(stop_event,),
        daemon=True,
        name="lifecycle-consumer",
    )
    lifecycle_thread.start()

    consumer = BatchConsumer(TOPIC_IN)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="llm-batch") as executor:
        try:
            while True:
                while pending and pending[0][0].done():
                    fut, msg = pending.popleft()
                    if fut.exception():
                        logger.error(f"Batch processing failed: {fut.exception()}")
                    consumer.commit(msg)

                if len(pending) >= concurrency:
                    time.sleep(0.05)
                    continue

                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                try:
                    proto_event = message_batch_pb2.MessageBatchEvent()
                    proto_event.ParseFromString(msg.value())
                    batch = proto_to_batch_event(proto_event)
                    logger.info(
                        f"Submitting batch {batch.event_id} ({len(batch.messages)} msgs) "
                        f"team={batch.team_id} [{len(pending)+1}/{concurrency}]"
                    )
                    fut = executor.submit(_process_and_publish_batch, batch)
                    pending.append((fut, msg))
                except Exception as e:
                    logger.error(f"Failed to parse Kafka message: {e}")
                    consumer.commit(msg)

        except KeyboardInterrupt:
            logger.info("Graceful shutdown initiated...")
            stop_event.set()
        finally:
            for fut, msg in pending:
                try:
                    fut.result(timeout=120)
                except Exception as e:
                    logger.error(f"Pending batch failed at shutdown: {e}")
                consumer.commit(msg)
            consumer.close()
            flush()
            transcript_thread.join(timeout=5)
            lifecycle_thread.join(timeout=5)


if __name__ == "__main__":
    main()
