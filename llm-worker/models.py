from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Kafka: Spring → LLM Worker ─────────────────────────────────────────────

class TranscriptReadyEvent(BaseModel):
    """Incoming event from audio.transcript.ready — Spring sends camelCase JSON."""
    model_config = ConfigDict(populate_by_name=True)

    file_id: str = Field(alias="fileId")
    team_id: str = Field(alias="teamId")
    bucket: str
    s3_key: str = Field(alias="s3Key")


class MessageDto(BaseModel):
    user_id: int
    username: str | None = None
    full_name: str
    text: str
    timestamp: datetime


class TeamMember(BaseModel):
    telegram_id: int
    username: str
    full_name: str
    role: str
    position: str | None = None


class ColumnInfo(BaseModel):
    id: str
    title: str


class MessageBatchEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    team_id: str
    team: list[TeamMember] = Field(default_factory=list)
    columns: list[ColumnInfo] = Field(default_factory=list)
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
    )


# ── Kafka: LLM Worker → Spring ──────────────────────────────────────────────

class TaskCreateEvent(BaseModel):
    team_id: str
    title: str
    description: str
    assignee: str | None = None
    assignee_id: int | None = None
    deadline: str | None = None
    column_id: str | None = None
    source_batch_id: str
    confidence: float = 0.0


class StatusChangeEvent(BaseModel):
    team_id: str
    task_hint: str
    assignee: str | None = None
    assignee_id: int | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]
    source_batch_id: str
    resolved_task_id: str | None = None


# ── LLM output — валидируем ответ модели ────────────────────────────────────

class ClassificationResult(BaseModel):
    has_task: bool = False
    confidence_task: float = 0.0
    has_status_change: bool = False
    confidence_status: float = 0.0


class TaskExtraction(BaseModel):
    title: str
    description: str
    assignee: str | None = None
    deadline: str | None = None
    column_id: str | None = None


class StatusExtraction(BaseModel):
    task_hint: str
    assignee: str | None = None
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


class StatusExtractionList(BaseModel):
    statuses: list[StatusExtraction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        if isinstance(data, list):
            return {"statuses": data}
        return data
