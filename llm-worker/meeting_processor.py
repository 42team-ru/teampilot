import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Union

from loguru import logger

from infra.kafka import publish
from infra.minio import download_file, list_object_keys, upload_file
from infra.qdrant import search_tasks, store_knowledge
from llm.chains import file_summary_chain, speaker_segments_chain
from models import (
    ColumnInfo,
    MeetingAudioChunkEvent,
    MeetingLiveResultEvent,
    MeetingSpeakerSegment,
    MeetingStatusPreview,
    MeetingTaskPreview,
    StickerInfo,
    StatusChangeEvent,
    TaskCreateEvent,
    TeamMember,
)
from processor import _process_transcript_chunk, _publish_transcript_events
from settings import settings

TOPIC_MEETING_RESULTS = "meetings.live.results"


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
