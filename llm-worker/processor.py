from datetime import datetime, timezone
from typing import List, Union

from loguru import logger
from pydantic import ValidationError

from infra.kafka import publish
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
)
from infra.minio import download_file
from settings import settings

TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"


def format_messages(batch: MessageBatchEvent) -> str:
    return "\n".join(
        f"[{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def format_team_context(batch: MessageBatchEvent) -> str:
    if not batch.team:
        return "TEAM LIST: not provided (use chat log usernames only)"

    lines = ["TEAM LIST (use this to resolve names and roles to @username):"]
    for m in batch.team:
        username = m.username if m.username.startswith("@") else f"@{m.username}"
        position_display = f"  [{m.position}]" if m.position else ""
        lines.append(f"  - {username}  |  {m.full_name}  |  {m.role}{position_display}")
    return "\n".join(lines)


def resolve_assignee_id(assignee: str | None, team: list[TeamMember]) -> int | None:
    if not assignee or not team:
        return None
    assignee_clean = assignee.lstrip("@").lower()
    for member in team:
        if member.username.lstrip("@").lower() == assignee_clean:
            return member.telegram_id
    return None


def build_column_map(batch: MessageBatchEvent) -> dict[str, str]:
    return {str(i + 1): col.id for i, col in enumerate(batch.columns)}


def format_columns_context(batch: MessageBatchEvent) -> tuple[str, dict[str, str]]:
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
    text = format_messages(batch)
    results = []

    try:
        clf_output = classifier_chain.invoke({"messages": text})
        clf = ClassificationResult.model_validate(clf_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Classifier failed (batch={batch.event_id}): {e}")
        return results

    logger.debug(f"Classification for batch {batch.event_id}: {clf}")

    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        results.extend(_extract_tasks(batch, text, clf.confidence_task))

    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        results.extend(_extract_statuses(batch, text))

    return results


def _extract_tasks(batch: MessageBatchEvent, text: str, confidence: float = 0.0) -> List[TaskCreateEvent]:
    try:
        columns_ctx, col_map = format_columns_context(batch)
        raw = task_chain.invoke({
            "messages": text,
            "current_datetime": batch.occurred_at.isoformat(),
            "team_context": format_team_context(batch),
            "columns_context": columns_ctx,
        })
        extraction_list = TaskExtractionList.model_validate(raw)

        events = []
        for extraction in extraction_list.tasks:
            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            task_data = extraction.model_dump()
            if task_data.get("deadline") and not task_data["deadline"].endswith("Z"):
                task_data["deadline"] = task_data["deadline"] + "Z"

            short_id = str(task_data.get("column_id") or "")
            task_data["column_id"] = col_map.get(short_id)

            events.append(TaskCreateEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                confidence=confidence,
                **task_data,
            ))

        return events
    except Exception as e:
        logger.error(f"Task extraction chain failed (batch={batch.event_id}): {e}")
        return []


def _extract_statuses(batch: MessageBatchEvent, text: str) -> List[StatusChangeEvent]:
    try:
        raw = status_chain.invoke({
            "messages": text,
            "team_context": format_team_context(batch),
        })
        extraction_list = StatusExtractionList.model_validate(raw)

        events = []
        for extraction in extraction_list.statuses:
            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            events.append(StatusChangeEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                resolved_task_id=None,
                **extraction.model_dump(),
            ))
        return events
    except Exception as e:
        logger.error(f"Status extraction chain failed (batch={batch.event_id}): {e}")
        return []


def _process_transcript_chunk(chunk: str, chunk_idx: int, event: TranscriptReadyEvent) -> None:
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
            for extraction in extraction_list.tasks:
                task_data = extraction.model_dump()
                task_data["column_id"] = None
                if task_data.get("deadline") and not task_data["deadline"].endswith("Z"):
                    task_data["deadline"] = task_data["deadline"] + "Z"
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
            for extraction in extraction_list.statuses:
                publish(TOPIC_STATUS, StatusChangeEvent(
                    team_id=event.team_id,
                    source_batch_id=event.file_id,
                    assignee_id=None,
                    resolved_task_id=None,
                    **extraction.model_dump(),
                ), key=event.file_id)
                logger.info(f"Transcript status published: {extraction.action} (chunk {chunk_idx})")
        except Exception as e:
            logger.error(f"Status extraction failed for transcript {event.file_id} chunk {chunk_idx}: {e}")


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
