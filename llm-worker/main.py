import time
import threading
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, List, Optional, Union

from loguru import logger
from pydantic import ValidationError

from infra.kafka import BatchConsumer, flush, publish
from infra.minio import download_file
from infra.qdrant import find_task_by_hint, init_collections, is_task_duplicate, store_batch, store_task
from llm.chains import classifier_chain, status_chain, task_chain
from llm.transcript import chunk_text
from models import (
    ClassificationResult,
    MessageBatchEvent,
    StatusChangeEvent,
    StatusExtractionList,
    TaskCreateEvent,
    TaskExtractionList,
    TeamMember,
    TranscriptReadyEvent,
    proto_to_batch_event,
)

from proto_generated.ru.team42.events import message_batch_pb2
from settings import settings

# Kafka Topic Constants
TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"
TOPIC_TRANSCRIPT = "audio.transcript.ready"


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


def format_team_context(batch: MessageBatchEvent) -> str:
    """
    Formats the team list into a readable context for the LLM.
    Includes Russian role synonyms to help LLaMA match slangy references.
    """
    if not batch.team:
        return "TEAM LIST: not provided (use chat log usernames only)"

    # Russian synonyms help LLaMA 8B map "девопс" → DevOps, "фронт" → Frontend, etc.
    role_synonyms: dict[str, str] = {
        "devops": "девопс",
        "developer": "разработчик",
        "frontend": "фронтенд/фронт",
        "backend": "бэкенд/бэк",
        "qa": "тестировщик/QA",
        "pm": "менеджер/PM",
        "lead": "лид/тимлид",
        "designer": "дизайнер",
    }

    lines = ["TEAM LIST (use this to resolve names and roles to @username):"]
    for m in batch.team:
        username = m.username if m.username.startswith("@") else f"@{m.username}"
        synonym = role_synonyms.get(m.role.lower(), "")
        role_display = f"{m.role} ({synonym})" if synonym else m.role
        position_display = f"  [{m.position}]" if m.position else ""
        lines.append(f"  - {username}  |  {m.full_name}  |  {role_display}{position_display}")
    return "\n".join(lines)


def resolve_assignee_id(assignee: str | None, team: list[TeamMember]) -> int | None:
    if not assignee or not team:
        return None
    assignee_clean = assignee.lstrip("@").lower()
    for member in team:
        if member.username.lstrip("@").lower() == assignee_clean:
            return member.telegram_id
    return None


_DONE_KEYWORDS = {"готово", "done", "завершен", "завершено", "закрыт", "closed", "complete"}
_PROGRESS_KEYWORDS = {"процесс", "progress", "работ", "in progress", "в работе", "делается"}
_TODO_KEYWORDS = {"бэклог", "backlog", "to do", "todo", "новые", "открыт", "очередь", "open", "queue"}


def _pick_column(columns: list, priority: str = "MEDIUM") -> "ColumnInfo":
    """Pick the right column based on priority. Never picks Done columns."""
    if not columns:
        return None

    def score(col) -> int:
        t = col.title.lower()
        if any(k in t for k in _DONE_KEYWORDS):
            return -10  # never for new tasks
        if priority == "HIGH" and any(k in t for k in _PROGRESS_KEYWORDS):
            return 20   # urgent → In Progress
        if any(k in t for k in _TODO_KEYWORDS):
            return 10   # default → Backlog/To Do
        if any(k in t for k in _PROGRESS_KEYWORDS):
            return 5
        return 1        # anything beats Done

    best = max(columns, key=score)
    if score(best) < 0:
        # All columns are "done" style — just use last
        return columns[-1]
    return best


def build_column_map(batch: MessageBatchEvent) -> dict[str, str]:
    """Returns {short_id -> real_uuid}, e.g. {"1": "b12e90bd-...", "2": "2933a06c-..."}"""
    return {str(i + 1): col.id for i, col in enumerate(batch.columns)}


def format_columns_context(batch: MessageBatchEvent) -> tuple[str, dict[str, str]]:
    """Returns (prompt_text, short_to_real mapping)."""
    if not batch.columns:
        return "KANBAN COLUMNS: not provided — set column_id = null", {}
    col_map = build_column_map(batch)
    real_to_short = {v: k for k, v in col_map.items()}
    lines = ["KANBAN COLUMNS (use the short id as column_id):"]
    for col in batch.columns:
        short = real_to_short[col.id]
        lines.append(f"  - column_id: \"{short}\"  |  title: \"{col.title}\"")
    return "\n".join(lines), col_map


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
    
    store_batch(batch.event_id, text, batch.team_id)

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
        task_events = _extract_tasks(batch, text)
        results.extend(task_events)

    # Step 3: Status Change Extraction (Expensive LLM)
    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        status_events = _extract_statuses(batch, text)
        results.extend(status_events)

    return results


def _extract_tasks(batch: MessageBatchEvent, text: str) -> List[TaskCreateEvent]:
    """
    Extracts one or more tasks from the batch text.
    Uses TaskExtractionList for per-item fault tolerance.
    """
    try:
        columns_ctx, col_map = format_columns_context(batch)
        raw = task_chain.invoke({
            "messages": text,
            "current_datetime": batch.occurred_at.isoformat(),
            "team_context": format_team_context(batch),
            "columns_context": columns_ctx,
        })
        extraction_list = TaskExtractionList.model_validate(raw)

        if extraction_list.failed_items > 0:
            logger.warning(
                f"Task extraction: {extraction_list.failed_items} item(s) failed "
                f"validation and were skipped (batch={batch.event_id})"
            )

        events = []
        for extraction in extraction_list.tasks:
            if is_task_duplicate(extraction.title, extraction.description or "", batch.team_id):
                logger.info(f"Duplicate task skipped: {extraction.title!r}")
                continue

            task_id = str(uuid.uuid4())
            store_task(task_id, extraction.title, extraction.description or "", batch.team_id)

            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            task_data = extraction.model_dump()

            # Map short id ("1","2","3") back to real UUID
            short_id = str(task_data.get("column_id") or "")
            real_id = col_map.get(short_id)
            if not real_id and batch.columns:
                fallback = _pick_column(batch.columns, task_data.get("priority", "MEDIUM"))
                real_id = fallback.id
                logger.warning(f"column_id={short_id!r} not in map → fallback '{fallback.title}'")
            task_data["column_id"] = real_id

            events.append(TaskCreateEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                **task_data,
            ))

        return events
    except Exception as e:
        logger.error(f"Task extraction chain failed (batch={batch.event_id}): {e}")
        return []


def _extract_statuses(batch: MessageBatchEvent, text: str) -> List[StatusChangeEvent]:
    """
    Extracts one or more status changes from the batch text.
    Uses StatusExtractionList for per-item fault tolerance.
    """
    try:
        raw = status_chain.invoke({
            "messages": text,
            "team_context": format_team_context(batch),
        })
        extraction_list = StatusExtractionList.model_validate(raw)

        if extraction_list.failed_items > 0:
            logger.warning(
                f"Status extraction: {extraction_list.failed_items} item(s) failed "
                f"validation and were skipped (batch={batch.event_id})"
            )

        events = []
        for extraction in extraction_list.statuses:
            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            resolved_task_id = find_task_by_hint(extraction.task_hint, batch.team_id)
            if resolved_task_id:
                logger.debug(f"Status hint {extraction.task_hint!r} resolved to task_id={resolved_task_id}")
            events.append(StatusChangeEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                resolved_task_id=resolved_task_id,
                **extraction.model_dump(),
            ))
        return events
    except Exception as e:
        logger.error(f"Status extraction chain failed (batch={batch.event_id}): {e}")
        return []



def _process_transcript_chunk(chunk: str, chunk_idx: int, event: TranscriptReadyEvent) -> None:
    """Process a single transcript chunk: classify → extract tasks + statuses."""
    try:
        clf_output = classifier_chain.invoke({"messages": chunk})
        clf = ClassificationResult.model_validate(clf_output)
    except Exception as e:
        logger.error(f"Classifier failed for transcript {event.file_id} chunk {chunk_idx}: {e}")
        return

    logger.debug(f"Transcript {event.file_id} chunk {chunk_idx} classification: {clf}")

    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        try:
            raw = task_chain.invoke({
                "messages": chunk,
                "current_datetime": datetime.now(timezone.utc).isoformat(),
                "team_context": "TEAM LIST: not provided",
                "columns_context": "KANBAN COLUMNS: not provided — set column_id = null",
            })
            extraction_list = TaskExtractionList.model_validate(raw)
            if extraction_list.failed_items > 0:
                logger.warning(
                    f"Transcript task extraction: {extraction_list.failed_items} item(s) skipped "
                    f"(file={event.file_id} chunk={chunk_idx})"
                )
            for extraction in extraction_list.tasks:
                if is_task_duplicate(extraction.title, extraction.description or "", event.team_id):
                    logger.info(f"Duplicate transcript task skipped: {extraction.title!r}")
                    continue
                task_id = str(uuid.uuid4())
                store_task(task_id, extraction.title, extraction.description or "", event.team_id)
                task_data = extraction.model_dump()
                task_data["column_id"] = None
                publish(TOPIC_TASKS, TaskCreateEvent(
                    team_id=event.team_id,
                    source_batch_id=event.file_id,
                    assignee_id=None,
                    **task_data,
                ), key=event.file_id)
                logger.info(f"Transcript task published: {extraction.title!r} (chunk {chunk_idx})")
        except Exception as e:
            logger.error(f"Task extraction failed for transcript {event.file_id} chunk {chunk_idx}: {e}")

    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        try:
            raw = status_chain.invoke({
                "messages": chunk,
                "team_context": "TEAM LIST: not provided",
            })
            extraction_list = StatusExtractionList.model_validate(raw)
            if extraction_list.failed_items > 0:
                logger.warning(
                    f"Transcript status extraction: {extraction_list.failed_items} item(s) skipped "
                    f"(file={event.file_id} chunk={chunk_idx})"
                )
            for extraction in extraction_list.statuses:
                resolved_task_id = find_task_by_hint(extraction.task_hint, event.team_id)
                if resolved_task_id:
                    logger.debug(
                        f"Transcript status hint {extraction.task_hint!r} → task_id={resolved_task_id}"
                    )
                publish(TOPIC_STATUS, StatusChangeEvent(
                    team_id=event.team_id,
                    source_batch_id=event.file_id,
                    assignee_id=None,
                    resolved_task_id=resolved_task_id,
                    **extraction.model_dump(),
                ), key=event.file_id)
                logger.info(f"Transcript status published: {extraction.action} (chunk {chunk_idx})")
        except Exception as e:
            logger.error(f"Status extraction failed for transcript {event.file_id} chunk {chunk_idx}: {e}")


def _process_and_publish_batch(batch: MessageBatchEvent) -> None:
    events = process_batch(batch)
    for event in events:
        if isinstance(event, TaskCreateEvent):
            publish(TOPIC_TASKS, event, key=str(batch.team_id))
            logger.info(f"Task event published: {event.title!r}")
        elif isinstance(event, StatusChangeEvent):
            publish(TOPIC_STATUS, event, key=str(batch.team_id))
            logger.info(f"Status event published: {event.action}")


def process_transcript(event: TranscriptReadyEvent) -> None:
    logger.info(f"Processing transcript file_id={event.file_id} from {event.bucket}/{event.s3_key}")

    try:
        text = download_file(event.bucket, event.s3_key).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to download transcript {event.s3_key}: {e}")
        return

    chunks = chunk_text(text)
    logger.info(f"Transcript {event.file_id}: {len(text)} chars → {len(chunks)} chunk(s)")

    for idx, chunk in enumerate(chunks):
        _process_transcript_chunk(chunk, idx, event)


def run_transcript_consumer(stop_event: threading.Event) -> None:
    consumer = BatchConsumer(TOPIC_TRANSCRIPT)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="llm-transcript") as executor:
        try:
            while not stop_event.is_set():
                # Коммитим завершённые в порядке поступления
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
    """
    Kafka Consumer loop entry point.
    """
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

    consumer = BatchConsumer(TOPIC_IN)
    pending: deque[tuple[Future, Any]] = deque()
    concurrency = settings.LLM_WORKER_CONCURRENCY

    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="llm-batch") as executor:
        try:
            while True:
                # Коммитим завершённые в порядке поступления (offset-безопасно)
                while pending and pending[0][0].done():
                    fut, msg = pending.popleft()
                    if fut.exception():
                        logger.error(f"Batch processing failed: {fut.exception()}")
                    consumer.commit(msg)

                # Backpressure: не берём новое, пока пул полон
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
            # Дожидаемся все in-flight задачи
            for fut, msg in pending:
                try:
                    fut.result(timeout=120)
                except Exception as e:
                    logger.error(f"Pending batch failed at shutdown: {e}")
                consumer.commit(msg)
            consumer.close()
            flush()
            transcript_thread.join(timeout=5)


if __name__ == "__main__":
    main()
