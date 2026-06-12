from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import re
from typing import List, Union

from loguru import logger
from pydantic import ValidationError

from infra.kafka import publish
from infra.qdrant import is_task_duplicate, search_knowledge, search_tasks, store_knowledge
from llm.chains import audio_status_chain, audio_task_chain, classifier_chain, decision_chain, file_summary_chain, status_chain, status_query_chain, task_chain
from llm.transcript import chunk_text
from models import (
    AudioNewEvent,
    ClassificationResult,
    ColumnInfo,
    DecisionExtractionList,
    FileSummaryEvent,
    MessageBatchEvent,
    StickerInfo,
    StatusChangeEvent,
    StatusExtractionList,
    TaskCreateEvent,
    TaskExtractionList,
    TeamMember,
)
from infra.minio import download_file, upload_file
from infra import debug_notifier
from settings import settings

TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"
TOPIC_FILE_SUMMARY = "files.transcript_ready"
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


def format_messages(batch: MessageBatchEvent) -> str:
    return "\n".join(
        f"[ID: {m.message_id or ''}] [{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def format_team_context(members: list[TeamMember]) -> str:
    if not members:
        return "TEAM LIST: not provided — set assignee_id = null"

    lines = ["TEAM LIST (output telegram_id as assignee_id — use ONLY values from this list):"]
    for m in members:
        username = m.username if m.username.startswith("@") else (f"@{m.username}" if m.username else "(no username)")
        position_display = f"  [{m.position}]" if m.position else ""
        lines.append(f"  - telegram_id: {m.telegram_id}  |  {username}  |  {m.full_name}  |  {m.role}{position_display}")
    return "\n".join(lines)


def format_stickers_context(stickers: list[StickerInfo]) -> str:
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


def build_column_map(columns: list[ColumnInfo]) -> dict[str, str]:
    return {str(i + 1): col.id for i, col in enumerate(columns)}


def format_columns_context(columns: list[ColumnInfo]) -> tuple[str, dict[str, str]]:
    if not columns:
        return "KANBAN COLUMNS: not provided — set column_id = null", {}
    col_map = build_column_map(columns)
    real_to_short = {v: k for k, v in col_map.items()}
    lines = ["KANBAN COLUMNS (use the short id as column_id):"]
    for col in columns:
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
        columns_ctx, col_map = format_columns_context(batch.columns)
        knowledge_items = search_knowledge(text, batch.team_id) if batch.team_id else []
        raw = task_chain.invoke({
            "messages": text,
            "current_datetime": batch.occurred_at.isoformat(),
            "team_context": format_team_context(batch.team),
            "columns_context": columns_ctx,
            "stickers_context": format_stickers_context(batch.stickers),
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
        columns_ctx, col_map = format_columns_context(batch.columns)

        raw = status_chain.invoke({
            "messages": text,
            "team_context": format_team_context(batch.team),
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


def _process_transcript_chunk(
    chunk: str,
    chunk_idx: int,
    file_id: str,
    team_id: str | None,
    team_members: list[TeamMember],
    columns: list[ColumnInfo],
    stickers: list[StickerInfo],
) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    events: List[Union[TaskCreateEvent, StatusChangeEvent]] = []
    try:
        clf_output = classifier_chain.invoke({"messages": chunk})
        clf = ClassificationResult.model_validate(clf_output)
    except Exception as e:
        logger.error(f"Classifier failed for transcript {file_id} chunk {chunk_idx}: {e}")
        return events

    logger.debug(f"Transcript {file_id} chunk {chunk_idx} classification: {clf}")

    team_ctx = format_team_context(team_members)
    columns_ctx, col_map = format_columns_context(columns)
    stickers_ctx = format_stickers_context(stickers)

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
    team_members: list[TeamMember] | None = None,
    columns: list[ColumnInfo] | None = None,
    stickers: list[StickerInfo] | None = None,
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
