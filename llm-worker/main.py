import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from loguru import logger

from infra.kafka import BatchConsumer, flush, publish
from infra.qdrant import (
    delete_knowledge,
    delete_task,
    ensure_collections,
    search_knowledge,
    store_knowledge,
    store_task,
)
from models import (
    AudioNewEvent,
    CourseIndexedEvent,
    CourseRecommendRequestEvent,
    CourseRecommendResultEvent,
    MeetingAudioChunkEvent,
    MessageBatchEvent,
    StatusChangeEvent,
    TaskCreateEvent,
    TaskLifecycleEvent,
    proto_to_batch_event,
)
from meeting_processor import process_meeting_audio
from processor import process_audio, process_batch
from proto_generated.ru.team42.events import message_batch_pb2
from settings import settings
from sync_processor import process_sync_request

TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"
TOPIC_AUDIO = "audio.new"
TOPIC_LIFECYCLE = "tasks.lifecycle"
TOPIC_SYNC_REQUESTS = "sync.requests"
TOPIC_MEETING_AUDIO = "meetings.audio.chunks"
TOPIC_COURSES_INDEXED = "courses.indexed"
TOPIC_COURSES_RECOMMEND_REQUEST = "courses.recommend.request"
TOPIC_COURSES_RECOMMEND_RESULT = "courses.recommend.result"


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


def run_sync_consumer(stop_event: threading.Event) -> None:
    from models import SyncRequestEvent
    consumer = BatchConsumer(TOPIC_SYNC_REQUESTS)
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                event = SyncRequestEvent.model_validate_json(msg.value().decode())
                process_sync_request(event)
            except Exception as e:
                logger.error(f"Error processing sync.requests: {e}")
            finally:
                consumer.commit(msg)
    finally:
        consumer.close()


def run_lifecycle_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_LIFECYCLE, settings.KAFKA_GROUP_ID_LIFECYCLE)
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                event = TaskLifecycleEvent.model_validate_json(msg.value().decode())
                if event.type in ("CONFIRMED", "UPDATED"):
                    store_task(
                        event.task_id,
                        event.title,
                        event.description or "",
                        event.team_id,
                    )
                    store_knowledge(
                        source_id=f"task:{event.task_id}",
                        team_id=event.team_id,
                        knowledge_type="task_archive",
                        content=f"{event.title}. {event.description or ''}".strip(". "),
                        title=event.title,
                    )
                    logger.info(f"Stored/updated task {event.task_id!r} in Qdrant")
                elif event.type == "CANCELLED":
                    delete_task(event.task_id)
                    delete_knowledge(f"task:{event.task_id}")
            except Exception as e:
                logger.error(f"Error processing lifecycle event: {e}")
            finally:
                consumer.commit(msg)
    finally:
        consumer.close()


def run_audio_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_AUDIO, settings.KAFKA_GROUP_ID_AUDIO)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="llm-audio",
    ) as executor:
        try:
            while not stop_event.is_set():
                while pending and pending[0][0].done():
                    fut, msg = pending.popleft()
                    if fut.exception():
                        logger.error(f"Audio processing failed: {fut.exception()}")
                    consumer.commit(msg)

                if len(pending) >= concurrency:
                    time.sleep(0.05)
                    continue

                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                try:
                    event = AudioNewEvent.model_validate_json(msg.value().decode())
                    fut = executor.submit(process_audio, event)
                    pending.append((fut, msg))
                except Exception as e:
                    logger.error(f"Error parsing audio.new event: {e}")
                    consumer.commit(msg)
        finally:
            for fut, msg in pending:
                try:
                    fut.result(timeout=120)
                except Exception as e:
                    logger.error(f"Pending audio failed at shutdown: {e}")
                consumer.commit(msg)
            consumer.close()


def run_meeting_audio_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_MEETING_AUDIO, settings.KAFKA_GROUP_ID_MEETING_AUDIO)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="llm-meeting-audio",
    ) as executor:
        try:
            while not stop_event.is_set():
                while pending and pending[0][0].done():
                    fut, msg = pending.popleft()
                    if fut.exception():
                        logger.error(
                            f"Meeting audio processing failed: {fut.exception()}"
                        )
                    consumer.commit(msg)

                if len(pending) >= concurrency:
                    time.sleep(0.05)
                    continue

                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                try:
                    event = MeetingAudioChunkEvent.model_validate_json(
                        msg.value().decode()
                    )
                    fut = executor.submit(process_meeting_audio, event)
                    pending.append((fut, msg))
                except Exception as e:
                    logger.error(f"Error parsing meetings.audio.chunks event: {e}")
                    consumer.commit(msg)
        finally:
            for fut, msg in pending:
                try:
                    fut.result(timeout=120)
                except Exception as e:
                    logger.error(f"Pending meeting audio failed at shutdown: {e}")
                consumer.commit(msg)
            consumer.close()


def run_course_indexed_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_COURSES_INDEXED, "llm-worker-courses-indexed")
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                event = CourseIndexedEvent.model_validate_json(msg.value().decode())
                content = (event.title + " " + (event.description or "")).strip()
                store_knowledge(
                    source_id=event.courseId,
                    team_id=event.teamId,
                    knowledge_type="course",
                    content=content,
                    title=event.title,
                )
                logger.info(f"Indexed course {event.courseId!r} team={event.teamId}")
            except Exception as e:
                logger.error(f"Error processing courses.indexed: {e}")
            finally:
                consumer.commit(msg)
    finally:
        consumer.close()


def run_course_recommend_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(
        TOPIC_COURSES_RECOMMEND_REQUEST,
        "llm-worker-courses-recommend",
    )
    try:
        while not stop_event.is_set():
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            try:
                event = CourseRecommendRequestEvent.model_validate_json(
                    msg.value().decode()
                )
                query = f"{event.taskTitle}. {event.taskDescription or ''}".strip(". ")
                results = search_knowledge(
                    query=query,
                    team_id=event.teamId,
                    knowledge_type="course",
                    extra_team_ids=["GLOBAL"],
                    limit=5,
                )
                course_ids = [r["source_id"] for r in results if r.get("source_id")]
                result_event = CourseRecommendResultEvent(
                    request_id=event.requestId,
                    task_id=event.taskId,
                    team_id=event.teamId,
                    course_ids=course_ids,
                )
                publish(
                    TOPIC_COURSES_RECOMMEND_RESULT,
                    result_event,
                    key=event.requestId,
                )
                logger.info(
                    "Course recommendation for taskId={!r}: found {} courses",
                    event.taskId,
                    len(course_ids),
                )
            except Exception as e:
                logger.error(f"Error processing courses.recommend.request: {e}")
            finally:
                consumer.commit(msg)
    finally:
        consumer.close()


def _run_http_server() -> None:
    import uvicorn

    from api import app

    uvicorn.run(app, host="0.0.0.0", port=settings.HTTP_PORT, log_level="warning")


def main() -> None:
    logger.info("LLM Worker starting in Kafka Consumer mode...")
    ensure_collections()

    http_thread = threading.Thread(
        target=_run_http_server,
        daemon=True,
        name="http-server",
    )
    http_thread.start()
    logger.info("HTTP API started on port {}", settings.HTTP_PORT)

    stop_event = threading.Event()
    audio_thread = threading.Thread(
        target=run_audio_consumer,
        args=(stop_event,),
        daemon=True,
        name="audio-consumer",
    )
    audio_thread.start()

    meeting_audio_thread = threading.Thread(
        target=run_meeting_audio_consumer,
        args=(stop_event,),
        daemon=True,
        name="meeting-audio-consumer",
    )
    meeting_audio_thread.start()

    lifecycle_thread = threading.Thread(
        target=run_lifecycle_consumer,
        args=(stop_event,),
        daemon=True,
        name="lifecycle-consumer",
    )
    lifecycle_thread.start()

    sync_thread = threading.Thread(
        target=run_sync_consumer,
        args=(stop_event,),
        daemon=True,
        name="sync-consumer",
    )
    sync_thread.start()

    course_indexed_thread = threading.Thread(
        target=run_course_indexed_consumer,
        args=(stop_event,),
        daemon=True,
        name="courses-indexed-consumer",
    )
    course_indexed_thread.start()

    course_recommend_thread = threading.Thread(
        target=run_course_recommend_consumer,
        args=(stop_event,),
        daemon=True,
        name="courses-recommend-consumer",
    )
    course_recommend_thread.start()

    consumer = BatchConsumer(TOPIC_IN, settings.KAFKA_GROUP_ID_BATCHES)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(
        max_workers=concurrency,
        thread_name_prefix="llm-batch",
    ) as executor:
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
                        "Submitting batch {} ({} msgs) team={} [{}/{}]",
                        batch.event_id,
                        len(batch.messages),
                        batch.team_id,
                        len(pending) + 1,
                        concurrency,
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
            audio_thread.join(timeout=5)
            meeting_audio_thread.join(timeout=5)
            lifecycle_thread.join(timeout=5)
            sync_thread.join(timeout=5)
            course_indexed_thread.join(timeout=5)
            course_recommend_thread.join(timeout=5)


if __name__ == "__main__":
    main()
