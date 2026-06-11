from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import re
import threading
import time
from typing import List, Union

from loguru import logger
from pydantic import ValidationError

from infra.kafka import publish
from infra.qdrant import is_task_duplicate, search_knowledge, search_tasks, store_knowledge
from llm.chains import audio_status_chain, audio_task_chain, classifier_chain, decision_chain, file_summary_chain, speaker_segments_chain, status_chain, status_query_chain, task_chain
from llm.transcript import chunk_text
from models import (
    AudioNewEvent,
    AudioColumnInfo,
    AudioTeamMember,
    AudioStickerInfo,
    ClassificationResult,
    DecisionExtractionList,
    FileSummaryEvent,
    MeetingAudioChunkEvent,
    MeetingLiveResultEvent,
    MeetingSpeakerSegment,
    MeetingStatusPreview,
    MeetingTaskPreview,
    MessageBatchEvent,
    StatusChangeEvent,
    StatusExtractionList,
    TaskCreateEvent,
    TaskExtractionList,
)
from infra.minio import download_file, list_object_keys, upload_file
from infra import debug_notifier
from settings import settings

TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"
TOPIC_FILE_SUMMARY = "files.transcript_ready"
TOPIC_MEETING_RESULTS = "meetings.live.results"
_MAX_STATUS_SEARCH_QUERIES = 6
_STATUS_SEARCH_MARKERS = (
    "готов",
    "сделал",
    "сделала",
    "сделали",
    "доделал",
    "доделала",
    "закрыл",
    "закрыла",
    "закрыли",
    "закончил",
    "закончила",
    "завершил",
    "завершила",
    "смотри в",
    "проверяй",
    "в мастере",
    "в pr",
    "в pull request",
    "задепло",
    "беру",
    "взял",
    "взяла",
    "приступил",
    "приступила",
    "начал",
    "начала",
    "отменяем",
    "отменить",
    "снимаем",
    "не актуально",
    "неактуально",
    "отбой",
    # completion verbs not covered above
    "разработал",
    "разработала",
    "настроил",
    "настроила",
    "выполнил",
    "выполнила",
    "реализовал",
    "реализовала",
    "написал",
    "написала",
    "исправил",
    "исправила",
    "запустил",
    "запустила",
    "прикрутил",
    "прикрутила",
    "починил",
    "починила",
    "обновил",
    "обновила",
    "задеплоил",
    "задеплоила",
    "смёрджил",
    "смерджил",
    "залил",
    "залила",
)


@dataclass
class MeetingTranscriptState:
    transcripts_by_chunk: dict[int, str] = field(default_factory=dict)
    last_extracted_chars: int = 0
    published_task_keys: set[str] = field(default_factory=set)
    published_status_keys: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class MeetingFinalizationResult:
    title: str
    description: str
    summary: str
    full_transcript: str
    recording_bucket: str
    recording_s3_key: str
    recording_content_type: str
    recording_size_bytes: int
    transcript_bucket: str
    transcript_s3_key: str
    finalized_at: datetime


_meeting_state: dict[str, MeetingTranscriptState] = {}
_meeting_state_lock = threading.Lock()


def format_messages(batch: MessageBatchEvent) -> str:
    return "\n".join(
        f"[ID: {m.message_id or ''}] [{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def format_team_context(batch: MessageBatchEvent) -> str:
    if not batch.team:
        return "TEAM LIST: not provided — set assignee_id = null"

    lines = ["TEAM LIST (output telegram_id as assignee_id — use ONLY values from this list):"]
    for m in batch.team:
        username = m.username if m.username.startswith("@") else f"@{m.username}"
        position_display = f"  [{m.position}]" if m.position else ""
        lines.append(f"  - telegram_id: {m.telegram_id}  |  {username}  |  {m.full_name}  |  {m.role}{position_display}")
    return "\n".join(lines)


def format_stickers_context(batch: MessageBatchEvent) -> str:
    if not batch.stickers:
        return "STICKERS: not provided — set stickers = null"
    lines = ["STICKERS (set sticker_id → state_id for each applicable sticker; omit if not applicable):"]
    for s in batch.stickers:
        if s.states:
            states_str = ", ".join(f'"{st.id}" ({st.title})' for st in s.states)
            lines.append(f'  - sticker_id: "{s.id}"  |  name: "{s.title}"  |  states: [{states_str}]')
        else:
            lines.append(f'  - sticker_id: "{s.id}"  |  name: "{s.title}"  |  free-text value')
    return "\n".join(lines)


def format_knowledge_context(items: list[dict]) -> str:
    if not items:
        return "KNOWLEDGE BASE: (empty — no relevant team knowledge found)"
    lines = ["KNOWLEDGE BASE (team decisions, meeting summaries, past tasks — use as background context):"]
    for item in items:
        kind = item.get("type", "")
        title = item.get("title", "")
        content = item.get("content", "")
        label = f"[{kind}]" + (f" {title}" if title else "")
        lines.append(f"  - {label}: {content}")
    return "\n".join(lines)


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


def _status_marker_index(text: str) -> int:
    lower = text.lower()
    indexes = [
        lower.find(marker)
        for marker in _STATUS_SEARCH_MARKERS
        if marker in lower
    ]
    return min(indexes) if indexes else -1



def _clean_status_search_query(text: str, limit: int = 320) -> str:
    # Strip formatter metadata like "[ID: ...] [10:00] username:" when the
    # fallback input is the already formatted batch text.
    cleaned = re.sub(r"^(?:\[[^\]]*]\s*)+", "", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if ": " in cleaned:
        prefix, rest = cleaned.split(": ", 1)
        if len(prefix) <= 80:
            cleaned = rest

    if len(cleaned) <= limit:
        return cleaned

    marker_idx = _status_marker_index(cleaned)
    if marker_idx < 0:
        return cleaned[:limit].rstrip()

    start = max(0, marker_idx - 120)
    end = min(len(cleaned), start + limit)
    return cleaned[start:end].strip()


def _dedupe_status_queries(queries: list[str]) -> list[str]:
    result = []
    seen = set()
    for query in queries:
        cleaned = _clean_status_search_query(query)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= _MAX_STATUS_SEARCH_QUERIES:
            break
    return result


def _status_queries_from_batch(batch: MessageBatchEvent) -> list[str]:
    text = format_messages(batch)
    queries = _status_queries_via_llm(text)
    if not queries:
        logger.debug("[STATUS QUERIES] LLM returned empty, falling back to raw message texts")
        queries = _dedupe_status_queries([m.text for m in batch.messages if m.text.strip()])
    return queries


def _status_queries_from_text(text: str) -> list[str]:
    queries = _status_queries_via_llm(text)
    if not queries:
        logger.debug("[STATUS QUERIES] LLM returned empty, falling back to raw text lines")
        lines = [l.strip() for l in re.split(r"[\n\r]+", text) if l.strip()]
        queries = _dedupe_status_queries(lines)
    return queries


def _status_queries_via_llm(text: str) -> list[str]:
    try:
        raw = status_query_chain.invoke({"messages": text})
        if not isinstance(raw, list):
            logger.warning(f"status_query_chain returned non-list: {raw!r}")
            return []
        queries = [str(q).strip() for q in raw if q and str(q).strip()]
        logger.debug(f"[STATUS QUERIES] extracted={queries}")
        return _dedupe_status_queries(queries)
    except Exception as e:
        logger.warning(f"status_query_chain failed: {e}")
        return []


def _merge_status_candidates(
    merged: dict[str, dict],
    candidate: dict,
    query: str,
) -> None:
    task_id = candidate.get("task_id")
    if not task_id:
        return

    score = float(candidate.get("rank_score") or candidate.get("score") or 0.0)
    existing = merged.setdefault(task_id, {**candidate, "matched_queries": []})

    existing_score = float(
        existing.get("rank_score") or existing.get("score") or 0.0
    )
    if score > existing_score:
        existing.update(candidate)

    matched_queries = existing.setdefault("matched_queries", [])
    if query not in matched_queries:
        matched_queries.append(query)


def _search_status_task_candidates(
    team_id: str | None,
    queries: list[str],
    limit: int = 5,
) -> list[dict]:
    if not team_id or not queries:
        return []

    merged: dict[str, dict] = {}
    for query in queries:
        for candidate in search_tasks(query, team_id, limit=limit):
            _merge_status_candidates(merged, candidate, query)

    return sorted(
        merged.values(),
        key=lambda candidate: (
            float(candidate.get("rank_score") or candidate.get("score") or 0.0),
            len(candidate.get("matched_queries") or []),
        ),
        reverse=True,
    )[:limit]


def process_batch(batch: MessageBatchEvent) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    text = format_messages(batch)
    results = []

    debug_notifier.notify_batch_received(batch.event_id, len(batch.messages), text)

    try:
        clf_output = classifier_chain.invoke({"messages": text})
        clf = ClassificationResult.model_validate(clf_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Classifier failed (batch={batch.event_id}): {e}")
        return results

    logger.debug(f"Classification for batch {batch.event_id}: {clf}")

    debug_notifier.notify_classification(
        batch.event_id,
        clf.has_task, clf.confidence_task,
        clf.has_status_change, clf.confidence_status,
        clf.has_decision, clf.confidence_decision,
    )

    run_tasks = clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD
    run_statuses = clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD
    run_decisions = clf.has_decision and clf.confidence_decision >= settings.CLASSIFIER_THRESHOLD

    n_workers = sum([run_tasks, run_statuses, run_decisions])
    if n_workers >= 2:
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            future_tasks = executor.submit(_extract_tasks, batch, text, clf.confidence_task) if run_tasks else None
            future_statuses = executor.submit(_extract_statuses, batch, text) if run_statuses else None
            future_decisions = executor.submit(_extract_decisions, batch, text) if run_decisions else None
            if future_tasks:
                results.extend(future_tasks.result())
            if future_statuses:
                results.extend(future_statuses.result())
            if future_decisions:
                future_decisions.result()
    else:
        if run_tasks:
            results.extend(_extract_tasks(batch, text, clf.confidence_task))
        elif run_statuses:
            results.extend(_extract_statuses(batch, text))
        elif run_decisions:
            _extract_decisions(batch, text)

    if not results and not run_decisions:
        debug_notifier.notify_no_results(batch.event_id)

    return results


def _extract_tasks(batch: MessageBatchEvent, text: str, confidence: float = 0.0) -> List[TaskCreateEvent]:
    try:
        columns_ctx, col_map = format_columns_context(batch)
        knowledge_items = search_knowledge(text, batch.team_id) if batch.team_id else []
        raw = task_chain.invoke({
            "messages": text,
            "current_datetime": batch.occurred_at.isoformat(),
            "team_context": format_team_context(batch),
            "columns_context": columns_ctx,
            "stickers_context": format_stickers_context(batch),
            "knowledge_context": format_knowledge_context(knowledge_items),
        })
        logger.debug(f"[TASK RAW] batch={batch.event_id} raw={raw!r}")
        extraction_list = TaskExtractionList.model_validate(raw)

        events = []
        for extraction in extraction_list.tasks:
            if is_task_duplicate(extraction.title, extraction.description or "", batch.team_id):
                logger.info(f"[TASK SKIP] duplicate title={extraction.title!r} team={batch.team_id}")
                continue

            task_data = extraction.model_dump()
            if task_data.get("deadline") and not task_data["deadline"].endswith("Z"):
                task_data["deadline"] = task_data["deadline"] + "Z"

            short_id = str(task_data.get("column_id") or "")
            task_data["column_id"] = col_map.get(short_id)

            if confidence > 0:
                task_data["description"] = (
                    task_data["description"] + f"\n\nУверенность ИИ: {confidence:.0%}"
                )

            event = TaskCreateEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                confidence=confidence,
                **task_data,
            )
            logger.info(
                f"[TASK] title={event.title!r} assignee={event.assignee_id} "
                f"deadline={event.deadline} column={event.column_id} confidence={confidence:.2f}"
            )
            events.append(event)

        debug_notifier.notify_tasks_extracted(batch.event_id, events)
        return events
    except Exception as e:
        logger.error(f"Task extraction chain failed (batch={batch.event_id}): {e}")
        return []


def format_task_candidates(candidates: list[dict]) -> str:
    if not candidates:
        return "TASK CANDIDATES: (none — Qdrant returned no matches)"
    lines = ["TASK CANDIDATES (select task_id ONLY from this list):"]
    for c in candidates:
        parts = [
            f'task_id: "{c["task_id"]}"',
            f'title: "{c["title"]}"',
        ]
        if c.get("description"):
            parts.append(f'description: "{c["description"]}"')
        if c.get("score") is not None:
            parts.append(f'score: {c["score"]:.3f}')
        if c.get("matched_kind"):
            parts.append(f'matched: {c["matched_kind"]}')
        if c.get("matched_queries"):
            queries = "; ".join(c["matched_queries"][:2])
            parts.append(f'query: "{queries}"')
        lines.append("  - " + "  |  ".join(parts))
    return "\n".join(lines)


def _extract_statuses(batch: MessageBatchEvent, text: str) -> List[StatusChangeEvent]:
    try:
        candidates = _search_status_task_candidates(
            batch.team_id,
            _status_queries_from_batch(batch),
            limit=5,
        )
        columns_ctx, col_map = format_columns_context(batch)

        raw = status_chain.invoke({
            "messages": text,
            "team_context": format_team_context(batch),
            "tasks_context": format_task_candidates(candidates),
            "columns_context": columns_ctx,
        })
        extraction_list = StatusExtractionList.model_validate(raw)

        events = []
        for extraction in extraction_list.statuses:
            data = extraction.model_dump()
            short_id = str(data.get("column_id") or "")
            data["column_id"] = col_map.get(short_id) or data.get("column_id")
            event = StatusChangeEvent(
                team_id=batch.team_id,
                source_batch_id=batch.event_id,
                **data,
            )
            logger.info(
                f"[STATUS] action={event.action} task_id={event.task_id} "
                f"column={event.column_id} assignee={event.assignee_id}"
            )
            events.append(event)

        debug_notifier.notify_statuses_extracted(batch.event_id, events)
        return events
    except Exception as e:
        logger.error(f"Status extraction chain failed (batch={batch.event_id}): {e}")
        return []


def _extract_decisions(batch: MessageBatchEvent, text: str) -> None:
    if not batch.team_id:
        return
    try:
        raw = decision_chain.invoke({"messages": text})
        extraction_list = DecisionExtractionList.model_validate(raw)
        for i, extraction in enumerate(extraction_list.decisions):
            if not extraction.text.strip():
                continue
            source_id = f"decision:{batch.event_id}:{i}"
            store_knowledge(
                source_id=source_id,
                team_id=batch.team_id,
                knowledge_type="decision",
                content=extraction.text,
            )
            logger.info(f"[DECISION] stored: {extraction.text!r} team={batch.team_id}")
    except Exception as e:
        logger.error(f"Decision extraction failed (batch={batch.event_id}): {e}")


def format_audio_team_context(members: list[AudioTeamMember]) -> str:
    if not members:
        return "TEAM LIST: not provided — set assignee_id = null"
    lines = ["TEAM LIST (output telegram_id as assignee_id — use ONLY values from this list):"]
    for m in members:
        username = m.username if m.username.startswith("@") else f"@{m.username}" if m.username else "(no username)"
        position_display = f"  [{m.position}]" if m.position else ""
        lines.append(f"  - telegram_id: {m.telegram_id}  |  {username}  |  {m.full_name}  |  {m.role}{position_display}")
    return "\n".join(lines)


def format_audio_columns_context(columns: list[AudioColumnInfo]) -> tuple[str, dict[str, str]]:
    if not columns:
        return "KANBAN COLUMNS: not provided — set column_id = null", {}
    col_map = {str(i + 1): col.id for i, col in enumerate(columns)}
    real_to_short = {v: k for k, v in col_map.items()}
    lines = ["KANBAN COLUMNS (use the short id as column_id):"]
    for col in columns:
        short = real_to_short[col.id]
        lines.append(f"  - column_id: \"{short}\"  |  title: \"{col.title}\"")
    return "\n".join(lines), col_map


def format_audio_stickers_context(stickers: list[AudioStickerInfo]) -> str:
    if not stickers:
        return "STICKERS: not provided — set stickers = null"
    lines = ["STICKERS (set sticker_id → state_id for each applicable sticker; omit if not applicable):"]
    for s in stickers:
        if s.states:
            states_str = ", ".join(f'"{st.id}" ({st.title})' for st in s.states)
            lines.append(f'  - sticker_id: "{s.id}"  |  name: "{s.title}"  |  states: [{states_str}]')
        else:
            lines.append(f'  - sticker_id: "{s.id}"  |  name: "{s.title}"  |  free-text value')
    return "\n".join(lines)


def _process_transcript_chunk(
    chunk: str,
    chunk_idx: int,
    file_id: str,
    team_id: str | None,
    team_members: list[AudioTeamMember],
    columns: list[AudioColumnInfo],
    stickers: list[AudioStickerInfo],
) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    events: List[Union[TaskCreateEvent, StatusChangeEvent]] = []
    try:
        clf_output = classifier_chain.invoke({"messages": chunk})
        clf = ClassificationResult.model_validate(clf_output)
    except Exception as e:
        logger.error(f"Classifier failed for transcript {file_id} chunk {chunk_idx}: {e}")
        return events

    logger.debug(f"Transcript {file_id} chunk {chunk_idx} classification: {clf}")

    team_ctx = format_audio_team_context(team_members)
    columns_ctx, col_map = format_audio_columns_context(columns)
    stickers_ctx = format_audio_stickers_context(stickers)

    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        try:
            raw = audio_task_chain.invoke({
                "messages": chunk,
                "current_datetime": datetime.now(timezone.utc).isoformat(),
                "team_context": team_ctx,
                "columns_context": columns_ctx,
                "stickers_context": stickers_ctx,
            })
            extraction_list = TaskExtractionList.model_validate(raw)
            for extraction in extraction_list.tasks:
                task_data = extraction.model_dump()
                short_id = str(task_data.get("column_id") or "")
                task_data["column_id"] = col_map.get(short_id)
                if task_data.get("deadline") and not task_data["deadline"].endswith("Z"):
                    task_data["deadline"] = task_data["deadline"] + "Z"
                audio_confidence = clf.confidence_task
                if audio_confidence > 0:
                    task_data["description"] = (
                        task_data["description"] + f"\n\nУверенность ИИ: {audio_confidence:.0%}"
                    )
                event = TaskCreateEvent(
                    team_id=team_id,
                    source_batch_id=file_id,
                    confidence=audio_confidence,
                    **task_data,
                )
                events.append(event)
                logger.info(f"Transcript task published: {extraction.title!r} (chunk {chunk_idx})")
        except Exception as e:
            logger.error(f"Task extraction failed for transcript {file_id} chunk {chunk_idx}: {e}")

    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        try:
            candidates = _search_status_task_candidates(
                team_id,
                _status_queries_from_text(chunk),
                limit=5,
            )
            raw = audio_status_chain.invoke({
                "messages": chunk,
                "team_context": team_ctx,
                "tasks_context": format_task_candidates(candidates),
                "columns_context": columns_ctx,
            })
            extraction_list = StatusExtractionList.model_validate(raw)
            for extraction in extraction_list.statuses:
                data = extraction.model_dump()
                short_id = str(data.get("column_id") or "")
                data["column_id"] = col_map.get(short_id) or data.get("column_id")
                event = StatusChangeEvent(
                    team_id=team_id,
                    source_batch_id=file_id,
                    **data,
                )
                events.append(event)
                logger.info(f"Transcript status published: {extraction.action} (chunk {chunk_idx})")
        except Exception as e:
            logger.error(f"Status extraction failed for transcript {file_id} chunk {chunk_idx}: {e}")

    return events


def _publish_transcript_events(events: List[Union[TaskCreateEvent, StatusChangeEvent]], key: str) -> None:
    for event in events:
        if isinstance(event, TaskCreateEvent):
            publish(TOPIC_TASKS, event, key=key)
        elif isinstance(event, StatusChangeEvent):
            publish(TOPIC_STATUS, event, key=key)


def process_transcript_text(
    text: str,
    file_id: str,
    team_id: str | None,
    team_members: list[AudioTeamMember] | None = None,
    columns: list[AudioColumnInfo] | None = None,
    stickers: list[AudioStickerInfo] | None = None,
) -> None:
    chunks = chunk_text(text)
    logger.info(f"Transcript {file_id}: {len(text)} chars → {len(chunks)} chunk(s)")
    for idx, chunk in enumerate(chunks):
        events = _process_transcript_chunk(
            chunk, idx, file_id, team_id,
            team_members or [], columns or [], stickers or [],
        )
        _publish_transcript_events(events, key=file_id)


def generate_file_summary(text: str, file_id: str, team_id: str | None) -> None:
    try:
        raw = file_summary_chain.invoke({"transcript": text})
        title = str(raw.get("title", "")).strip()[:100] or f"Запись {file_id[:8]}"
        description = str(raw.get("description", "")).strip()
        summary = str(raw.get("summary", "")).strip()

        if not title:
            logger.warning(f"File summary returned empty title for file_id={file_id}")
            return

        event = FileSummaryEvent(
            file_id=file_id,
            team_id=team_id,
            title=title,
            description=description,
            summary=summary,
        )
        publish(TOPIC_FILE_SUMMARY, event, key=file_id)
        logger.info(f"File summary published for file_id={file_id} title={title!r}")

        if team_id and summary:
            store_knowledge(
                source_id=f"file:{file_id}",
                team_id=team_id,
                knowledge_type="file_summary",
                content=summary,
                title=title,
            )
    except Exception as e:
        logger.error(f"File summary generation failed for file_id={file_id}: {e}")



def process_audio(event: AudioNewEvent) -> None:
    from infra.audio import to_whisper_wav
    from infra.whisper import transcribe

    logger.info(f"Processing audio file_id={event.file_id} from {event.bucket}/{event.s3_key}")

    try:
        audio_bytes = download_file(event.bucket, event.s3_key)
    except Exception as e:
        logger.error(f"Failed to download audio {event.s3_key}: {e}")
        return

    try:
        wav_bytes = to_whisper_wav(audio_bytes)
        filename = event.original_filename if event.original_filename.endswith(".wav") else event.original_filename + ".wav"
        text = transcribe(wav_bytes, filename)
    except Exception as e:
        logger.error(f"Whisper transcription failed for file_id={event.file_id}: {e}")
        return

    logger.info(f"Transcribed file_id={event.file_id}: {len(text)} chars")
    debug_notifier.notify_transcript(event.file_id, len(text), text)

    try:
        base_key, _ = os.path.splitext(event.s3_key)
        transcript_key = base_key + ".txt"
        logger.info(f"Uploading transcript to {event.bucket}/{transcript_key}")
        upload_file(
            event.bucket,
            transcript_key,
            text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        logger.error(f"Failed to upload transcript to MinIO: {e}")

    process_transcript_text(
        text, event.file_id, event.team_id,
        team_members=event.team,
        columns=event.columns,
        stickers=event.stickers,
    )
    generate_file_summary(text, event.file_id, event.team_id)


def _meeting_context_after_chunk(meeting_id: str, chunk_index: int, transcript: str) -> tuple[str, bool]:
    with _meeting_state_lock:
        state = _meeting_state.setdefault(meeting_id, MeetingTranscriptState())
        state.transcripts_by_chunk[chunk_index] = transcript

        full_text = "\n".join(
            text
            for _, text in sorted(state.transcripts_by_chunk.items())
            if text.strip()
        ).strip()
        context = full_text[-settings.MEETING_CONTEXT_CHARS:]
        new_chars = max(0, len(full_text) - state.last_extracted_chars)
        should_extract = (
            len(context) >= settings.MEETING_EXTRACTION_MIN_CHARS
            and new_chars >= settings.MEETING_EXTRACTION_STEP_CHARS
        )
        if should_extract:
            state.last_extracted_chars = len(full_text)
        return context, should_extract


def _meeting_full_context(meeting_id: str) -> str:
    with _meeting_state_lock:
        state = _meeting_state.setdefault(meeting_id, MeetingTranscriptState())
        return "\n".join(
            text
            for _, text in sorted(state.transcripts_by_chunk.items())
            if text.strip()
        ).strip()


def _meeting_chunks_prefix(meeting_id: str) -> str:
    return f"meetings/{meeting_id}/chunks/"


def _chunk_index_from_key(key: str) -> int | None:
    filename = key.rsplit("/", 1)[-1]
    chunk_number = filename.split("-", 1)[0]
    try:
        return int(chunk_number)
    except ValueError:
        return None


def _meeting_chunk_object_keys(bucket: str, meeting_id: str, final_chunk_index: int | None = None) -> list[str]:
    keys = list_object_keys(bucket, _meeting_chunks_prefix(meeting_id))
    keyed_by_index: dict[int, str] = {}
    skipped_keys: list[str] = []

    for key in keys:
        index = _chunk_index_from_key(key)
        if index is None:
            skipped_keys.append(key)
            continue
        if final_chunk_index is not None and index > final_chunk_index:
            continue
        keyed_by_index[index] = key

    if skipped_keys:
        logger.warning(
            "Skipped meeting chunk objects with unparsable index meeting_id={} keys={}",
            meeting_id,
            skipped_keys,
        )

    return [
        keyed_by_index[index]
        for index in sorted(keyed_by_index)
    ]


def _wait_for_meeting_chunk_objects(bucket: str, meeting_id: str, final_chunk_index: int) -> list[str]:
    expected = set(range(final_chunk_index + 1))
    deadline = time.monotonic() + settings.MEETING_FINALIZE_WAIT_SECONDS
    keys: list[str] = []

    while True:
        try:
            keys = _meeting_chunk_object_keys(bucket, meeting_id, final_chunk_index)
        except Exception as e:
            logger.error(
                "Failed to list meeting chunks meeting_id={} bucket={}: {}",
                meeting_id,
                bucket,
                e,
            )
            if time.monotonic() >= deadline:
                break
            time.sleep(0.2)
            continue

        indexes = {
            index
            for key in keys
            if (index := _chunk_index_from_key(key)) is not None
        }
        if expected.issubset(indexes):
            return keys
        if time.monotonic() >= deadline:
            break
        time.sleep(0.2)

    indexes = {
        index
        for key in keys
        if (index := _chunk_index_from_key(key)) is not None
    }
    missing_chunks = sorted(expected - indexes)

    logger.warning(
        "Finalizing meeting with missing MinIO chunks meeting_id={} missing_chunks={}",
        meeting_id,
        missing_chunks,
    )
    return keys


def _mark_meeting_final_extract(meeting_id: str) -> None:
    with _meeting_state_lock:
        state = _meeting_state.setdefault(meeting_id, MeetingTranscriptState())
        state.last_extracted_chars = sum(len(t) for t in state.transcripts_by_chunk.values())


def _filter_new_meeting_events(
    meeting_id: str,
    events: List[Union[TaskCreateEvent, StatusChangeEvent]],
) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    result: List[Union[TaskCreateEvent, StatusChangeEvent]] = []
    with _meeting_state_lock:
        state = _meeting_state.setdefault(meeting_id, MeetingTranscriptState())
        for event in events:
            if isinstance(event, TaskCreateEvent):
                key = event.title.strip().lower()
                if not key or key in state.published_task_keys:
                    continue
                state.published_task_keys.add(key)
                result.append(event)
            elif isinstance(event, StatusChangeEvent):
                key = "|".join([
                    event.action,
                    event.task_id or "",
                    str(event.assignee_id or ""),
                    event.column_id or "",
                ])
                if key in state.published_status_keys:
                    continue
                state.published_status_keys.add(key)
                result.append(event)
    return result


def _summarize_meeting_context(context: str, meeting_id: str) -> str:
    if not context.strip():
        return ""
    try:
        raw = file_summary_chain.invoke({"transcript": context})
        summary = str(raw.get("summary", "")).strip()
        description = str(raw.get("description", "")).strip()
        return summary or description
    except Exception as e:
        logger.error(f"Meeting summary generation failed meeting_id={meeting_id}: {e}")
        return context[-1200:]


def _generate_meeting_final_summary(full_transcript: str, meeting_id: str) -> tuple[str, str, str]:
    if not full_transcript.strip():
        return f"Митинг {meeting_id[:8]}", "", ""
    try:
        raw = file_summary_chain.invoke({"transcript": full_transcript})
        title = str(raw.get("title", "")).strip()[:100] or f"Митинг {meeting_id[:8]}"
        description = str(raw.get("description", "")).strip()
        summary = str(raw.get("summary", "")).strip()
        return title, description, summary
    except Exception as e:
        logger.error(f"Final meeting summary generation failed meeting_id={meeting_id}: {e}")
        return f"Митинг {meeting_id[:8]}", "", full_transcript[-1200:]


def _extract_meeting_speaker_segments(full_transcript: str, meeting_id: str) -> list[MeetingSpeakerSegment]:
    text = full_transcript.strip()
    if not text:
        return []
    try:
        raw = speaker_segments_chain.invoke({"transcript": text[:12000]})
    except Exception as e:
        logger.error("Speaker segment extraction failed meeting_id={}: {}", meeting_id, e)
        return []

    items = raw if isinstance(raw, list) else raw.get("speakers") if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return []

    result: list[MeetingSpeakerSegment] = []
    seen: set[str] = set()
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        label = str(item.get("speaker_label") or item.get("speakerLabel") or f"SPEAKER_{idx}").strip().upper()
        if not re.fullmatch(r"SPEAKER_\d{1,2}", label):
            label = f"SPEAKER_{idx}"
        if label in seen:
            continue
        sample = str(item.get("sample") or item.get("text") or "").strip()
        if not sample:
            continue
        result.append(MeetingSpeakerSegment(speaker_label=label, sample=sample[:180]))
        seen.add(label)
        if len(result) >= 6:
            break
    return result


def _finalize_meeting_recording(event: MeetingAudioChunkEvent) -> MeetingFinalizationResult | None:
    from infra.audio import merge_audio_chunks, to_whisper_wav
    from infra.whisper import transcribe

    chunk_keys = _wait_for_meeting_chunk_objects(event.bucket, event.meeting_id, event.chunk_index)
    if not chunk_keys:
        logger.warning("No MinIO chunks found for final meeting recording meeting_id={}", event.meeting_id)
        return None

    audio_chunks = []
    for key in chunk_keys:
        try:
            audio_chunks.append(download_file(event.bucket, key))
        except Exception as e:
            logger.error(
                "Failed to download meeting chunk for final recording meeting_id={} key={}: {}",
                event.meeting_id,
                key,
                e,
            )
            return None

    recording_bytes, recording_content_type, extension = merge_audio_chunks(audio_chunks)
    if not recording_bytes:
        logger.error("Meeting recording merge returned empty file meeting_id={}", event.meeting_id)
        return None

    bucket = event.bucket
    base_key = f"meetings/{event.meeting_id}/final"
    recording_key = f"{base_key}/recording.{extension}"
    transcript_key = f"{base_key}/transcript.txt"

    try:
        upload_file(bucket, recording_key, recording_bytes, content_type=recording_content_type)
    except Exception as e:
        logger.error("Failed to upload final meeting recording meeting_id={}: {}", event.meeting_id, e)
        return None

    try:
        wav_bytes = to_whisper_wav(recording_bytes)
        full_transcript = transcribe(wav_bytes, f"meeting-{event.meeting_id}.{extension}").strip()
    except Exception as e:
        logger.error("Full meeting transcription failed meeting_id={}: {}", event.meeting_id, e)
        return None

    try:
        upload_file(
            bucket,
            transcript_key,
            full_transcript.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
    except Exception as e:
        logger.error("Failed to upload final meeting transcript meeting_id={}: {}", event.meeting_id, e)
        return None

    title, description, summary = _generate_meeting_final_summary(full_transcript, event.meeting_id)
    return MeetingFinalizationResult(
        title=title,
        description=description,
        summary=summary,
        full_transcript=full_transcript,
        recording_bucket=bucket,
        recording_s3_key=recording_key,
        recording_content_type=recording_content_type,
        recording_size_bytes=len(recording_bytes),
        transcript_bucket=bucket,
        transcript_s3_key=transcript_key,
        finalized_at=datetime.now(timezone.utc),
    )


def _to_meeting_task_preview(event: TaskCreateEvent) -> MeetingTaskPreview:
    return MeetingTaskPreview(
        title=event.title,
        description=event.description,
        assignee_id=event.assignee_id,
        deadline=event.deadline,
        column_id=event.column_id,
        confidence=event.confidence,
    )


def _to_meeting_status_preview(event: StatusChangeEvent) -> MeetingStatusPreview:
    return MeetingStatusPreview(
        task_id=event.task_id,
        assignee_id=event.assignee_id,
        column_id=event.column_id,
        action=event.action,
    )


def process_meeting_audio(event: MeetingAudioChunkEvent) -> None:
    from infra.audio import to_whisper_wav
    from infra.whisper import transcribe

    logger.info(
        "Processing meeting chunk meeting_id={} chunk={} from {}/{}",
        event.meeting_id,
        event.chunk_index,
        event.bucket,
        event.s3_key,
    )

    try:
        audio_bytes = download_file(event.bucket, event.s3_key)
    except Exception as e:
        logger.error(f"Failed to download meeting audio {event.s3_key}: {e}")
        return

    try:
        wav_bytes = to_whisper_wav(audio_bytes)
        filename = event.original_filename if event.original_filename.endswith(".wav") else event.original_filename + ".wav"
        transcript = transcribe(wav_bytes, filename).strip()
    except Exception as e:
        logger.error(f"Whisper transcription failed for meeting_id={event.meeting_id} chunk={event.chunk_index}: {e}")
        return

    context, should_extract = _meeting_context_after_chunk(event.meeting_id, event.chunk_index, transcript)
    if event.final_chunk:
        context = _meeting_full_context(event.meeting_id)
        should_extract = True
        _mark_meeting_final_extract(event.meeting_id)

    extracted_events: List[Union[TaskCreateEvent, StatusChangeEvent]] = []
    summary = ""
    finalization: MeetingFinalizationResult | None = None
    speaker_segments: list[MeetingSpeakerSegment] = []
    if should_extract and context:
        extracted_events = _process_transcript_chunk(
            context,
            event.chunk_index,
            f"{event.meeting_id}:{event.chunk_index}",
            event.team_id,
            event.team,
            event.columns,
            event.stickers,
        )
        extracted_events = _filter_new_meeting_events(event.meeting_id, extracted_events)
        _publish_transcript_events(extracted_events, key=event.meeting_id)
        summary = _summarize_meeting_context(context, event.meeting_id)

    hints: list[str] = []
    if event.team_id is not None:
        for e in extracted_events:
            if isinstance(e, TaskCreateEvent):
                similar = search_tasks(e.title, event.team_id, limit=1, score_threshold=0.80)
                if similar:
                    hints.append(f"Похожая задача уже есть: «{similar[0]['title']}»")

    if event.final_chunk:
        finalization = _finalize_meeting_recording(event)
        if finalization is not None:
            transcript = finalization.full_transcript
            context = finalization.full_transcript
            summary = finalization.summary
            speaker_segments = _extract_meeting_speaker_segments(finalization.full_transcript, event.meeting_id)
            if event.team_id and finalization.summary:
                store_knowledge(
                    source_id=f"meeting:{event.meeting_id}",
                    team_id=event.team_id,
                    knowledge_type="meeting_summary",
                    content=finalization.summary,
                    title=finalization.title,
                )
            if finalization.full_transcript:
                full_events = _process_transcript_chunk(
                    finalization.full_transcript,
                    event.chunk_index,
                    f"{event.meeting_id}:full",
                    event.team_id,
                    event.team,
                    event.columns,
                    event.stickers,
                )
                new_full_events = _filter_new_meeting_events(event.meeting_id, full_events)
                _publish_transcript_events(new_full_events, key=event.meeting_id)
                extracted_events = extracted_events + new_full_events
                if event.team_id is not None:
                    for e in new_full_events:
                        if isinstance(e, TaskCreateEvent):
                            similar = search_tasks(e.title, event.team_id, limit=1, score_threshold=0.80)
                            if similar:
                                hints.append(f"Похожая задача уже есть: «{similar[0]['title']}»")
                logger.info(
                    "Full transcript re-extraction meeting_id={} new_events={} total_events={}",
                    event.meeting_id,
                    len(new_full_events),
                    len(extracted_events),
                )

    tasks = [
        _to_meeting_task_preview(e)
        for e in extracted_events
        if isinstance(e, TaskCreateEvent)
    ]
    statuses = [
        _to_meeting_status_preview(e)
        for e in extracted_events
        if isinstance(e, StatusChangeEvent)
    ]

    publish(
        TOPIC_MEETING_RESULTS,
        MeetingLiveResultEvent(
            meeting_id=event.meeting_id,
            team_id=event.team_id,
            chunk_index=event.chunk_index,
            transcript=transcript,
            summary=summary,
            context=context,
            final_result=finalization is not None,
            title=finalization.title if finalization is not None else None,
            description=finalization.description if finalization is not None else None,
            recording_bucket=finalization.recording_bucket if finalization is not None else None,
            recording_s3_key=finalization.recording_s3_key if finalization is not None else None,
            recording_content_type=finalization.recording_content_type if finalization is not None else None,
            recording_size_bytes=finalization.recording_size_bytes if finalization is not None else None,
            transcript_bucket=finalization.transcript_bucket if finalization is not None else None,
            transcript_s3_key=finalization.transcript_s3_key if finalization is not None else None,
            finalized_at=finalization.finalized_at if finalization is not None else None,
            tasks=tasks,
            statuses=statuses,
            hints=hints,
            speaker_segments=speaker_segments,
        ),
        key=event.meeting_id,
    )
    logger.info(
        "Meeting result published meeting_id={} chunk={} transcript_chars={} tasks={} statuses={}",
        event.meeting_id,
        event.chunk_index,
        len(transcript),
        len(tasks),
        len(statuses),
    )
    print(f"{transcript}")
