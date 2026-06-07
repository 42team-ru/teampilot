from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Kafka: Spring → LLM Worker ─────────────────────────────────────────────

class AudioTeamMember(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    telegram_id: int = Field(alias="telegramId")
    username: str = ""
    full_name: str = Field(alias="fullName", default="")
    role: str = ""
    position: str | None = None


class AudioColumnInfo(BaseModel):
    id: str
    title: str


class AudioStickerState(BaseModel):
    id: str
    title: str


class AudioStickerInfo(BaseModel):
    id: str
    title: str
    type: str
    states: list[AudioStickerState] = Field(default_factory=list)


class AudioNewEvent(BaseModel):
    """Incoming event from audio.new — Spring sends camelCase JSON."""
    model_config = ConfigDict(populate_by_name=True)

    file_id: str = Field(alias="fileId")
    team_id: str | None = Field(alias="teamId", default=None)
    team_chat_id: int | None = Field(alias="teamChatId", default=None)
    bucket: str
    s3_key: str = Field(alias="s3Key")
    original_filename: str = Field(alias="originalFilename", default="audio")
    content_type: str = Field(alias="contentType", default="audio/ogg")
    team: list[AudioTeamMember] = Field(default_factory=list)
    columns: list[AudioColumnInfo] = Field(default_factory=list)
    stickers: list[AudioStickerInfo] = Field(default_factory=list)


class MeetingAudioChunkEvent(BaseModel):
    """Incoming event from meetings.audio.chunks — Spring sends camelCase JSON."""
    model_config = ConfigDict(populate_by_name=True)

    meeting_id: str = Field(alias="meetingId")
    team_id: str = Field(alias="teamId")
    recorder_telegram_id: int | None = Field(alias="recorderTelegramId", default=None)
    chunk_index: int = Field(alias="chunkIndex")
    final_chunk: bool = Field(alias="finalChunk", default=False)
    bucket: str
    s3_key: str = Field(alias="s3Key")
    original_filename: str = Field(alias="originalFilename", default="meeting-chunk")
    content_type: str = Field(alias="contentType", default="audio/webm")
    team: list[AudioTeamMember] = Field(default_factory=list)
    columns: list[AudioColumnInfo] = Field(default_factory=list)
    stickers: list[AudioStickerInfo] = Field(default_factory=list)


class MessageDto(BaseModel):
    user_id: int
    username: str | None = None
    full_name: str
    text: str
    timestamp: datetime
    message_id: str | None = None


class TeamMember(BaseModel):
    telegram_id: int
    username: str
    full_name: str
    role: str
    position: str | None = None


class ColumnInfo(BaseModel):
    id: str
    title: str


class StickerStateInfo(BaseModel):
    id: str
    title: str


class StickerInfo(BaseModel):
    id: str
    title: str
    type: str
    states: list[StickerStateInfo] = Field(default_factory=list)


class MessageBatchEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    team_id: str
    team: list[TeamMember] = Field(default_factory=list)
    columns: list[ColumnInfo] = Field(default_factory=list)
    stickers: list[StickerInfo] = Field(default_factory=list)
    messages: list[MessageDto]
    batch_start: datetime
    batch_end: datetime


def proto_to_batch_event(proto_event: Any) -> MessageBatchEvent:
    """Convert proto-generated MessageBatchEvent to Pydantic model."""
    def ts_to_dt(ts: Any) -> datetime:
        return datetime.fromtimestamp(ts.seconds + ts.nanos / 1e9, tz=timezone.utc)

    return MessageBatchEvent(
        event_id=proto_event.event_id,
        occurred_at=ts_to_dt(proto_event.occurred_at),
        team_id=proto_event.team_id,
        batch_start=ts_to_dt(proto_event.batch_start),
        batch_end=ts_to_dt(proto_event.batch_end),
        messages=[
            MessageDto(
                user_id=m.user_id,
                username=m.username or None,
                full_name=m.full_name,
                text=m.text,
                timestamp=ts_to_dt(m.timestamp),
                message_id=m.message_id or None,
            )
            for m in proto_event.messages
        ],
        team=[
            TeamMember(
                telegram_id=t.telegram_id,
                username=t.username,
                full_name=t.full_name,
                role=t.role,
                position=t.position or None,
            )
            for t in proto_event.team
        ],
        columns=[
            ColumnInfo(id=c.id, title=c.title)
            for c in proto_event.columns
        ],
        stickers=[
            StickerInfo(
                id=s.id,
                title=s.title,
                type=s.type,
                states=[StickerStateInfo(id=st.id, title=st.title) for st in s.states],
            )
            for s in proto_event.stickers
        ],
    )


# ── Kafka: LLM Worker → Spring ──────────────────────────────────────────────

class FileSummaryEvent(BaseModel):
    file_id: str
    team_id: str | None
    title: str
    description: str
    summary: str


class TaskCreateEvent(BaseModel):
    team_id: str
    title: str
    description: str
    assignee_id: int | None = None
    deadline: str | None = None
    column_id: str | None = None
    source_batch_id: str
    confidence: float = 0.0
    source_message_ids: list[str] = Field(default_factory=list)
    stickers: dict[str, str] | None = None


class StatusChangeEvent(BaseModel):
    team_id: str
    task_id: str | None = None
    assignee_id: int | None = None
    column_id: str | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]
    source_batch_id: str


class MeetingTaskPreview(BaseModel):
    title: str
    description: str
    assignee_id: int | None = None
    deadline: str | None = None
    column_id: str | None = None
    confidence: float = 0.0


class MeetingStatusPreview(BaseModel):
    task_id: str | None = None
    assignee_id: int | None = None
    column_id: str | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]


class MeetingLiveResultEvent(BaseModel):
    meeting_id: str
    team_id: str
    chunk_index: int
    transcript: str
    summary: str = ""
    context: str = ""
    final_result: bool = False
    title: str | None = None
    description: str | None = None
    recording_bucket: str | None = None
    recording_s3_key: str | None = None
    recording_content_type: str | None = None
    recording_size_bytes: int | None = None
    transcript_bucket: str | None = None
    transcript_s3_key: str | None = None
    finalized_at: datetime | None = None
    tasks: list[MeetingTaskPreview] = Field(default_factory=list)
    statuses: list[MeetingStatusPreview] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)


# ── LLM output — валидируем ответ модели ────────────────────────────────────

class ClassificationResult(BaseModel):
    has_task: bool = False
    confidence_task: float = 0.0
    has_status_change: bool = False
    confidence_status: float = 0.0
    has_decision: bool = False
    confidence_decision: float = 0.0


class TaskExtraction(BaseModel):
    title: str
    description: str
    assignee_id: int | None = None
    deadline: str | None = None
    column_id: str | None = None
    source_message_ids: list[str] = Field(default_factory=list)
    stickers: dict[str, str] | None = None


class StatusExtraction(BaseModel):
    task_id: str | None = None
    assignee_id: int | None = None
    column_id: str | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]


class TaskExtractionList(BaseModel):
    tasks: list[TaskExtraction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        if isinstance(data, list):
            return {"tasks": data}
        return data


class TaskLifecycleEvent(BaseModel):
    """Incoming event from tasks.lifecycle — Spring sends camelCase JSON."""
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    task_id: str = Field(alias="taskId")
    team_id: str = Field(alias="teamId")
    type: Literal["CONFIRMED", "UPDATED", "CANCELLED"]
    title: str
    description: str | None = None


class DecisionExtraction(BaseModel):
    text: str


class DecisionExtractionList(BaseModel):
    decisions: list[DecisionExtraction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        if isinstance(data, list):
            return {"decisions": data}
        return data


class StatusExtractionList(BaseModel):
    statuses: list[StatusExtraction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        if isinstance(data, list):
            return {"statuses": data}
        return data
