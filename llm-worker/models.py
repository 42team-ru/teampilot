from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


# ── Kafka: Spring → LLM Worker ─────────────────────────────────────────────

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
    chat_id: int
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
        chat_id=proto_event.chat_id,
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
    chat_id: int
    title: str
    description: str
    assignee: str | None = None
    assignee_id: int | None = None
    deadline: str | None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    source_batch_id: str


class StatusChangeEvent(BaseModel):
    chat_id: int
    task_hint: str
    assignee: str | None = None
    assignee_id: int | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]
    source_batch_id: str


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
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class StatusExtraction(BaseModel):
    task_hint: str
    assignee: str | None = None
    action: Literal["COMPLETE", "ASSIGN", "CANCEL"]


# ── Fault-tolerant list wrappers ─────────────────────────────────────────────
# Принимают сырой JSON-массив от LLM: [{...}, {...}]
# Плохие элементы отбрасываются молча; failed_items — для логирования в main.py

class TaskExtractionList(BaseModel):
    """
    Fault-tolerant wrapper для ответа task_chain.

    LLaMA возвращает JSON-массив. Каждый элемент валидируется отдельно.
    Если один элемент кривой — остальные задачи всё равно создаются.
    """
    tasks: list[TaskExtraction] = Field(default_factory=list)
    failed_items: int = Field(default=0, exclude=True)  # исключён из model_dump()

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        """Принимает и список [{...}] и словарь {"tasks": [...]} — оба формата."""
        if isinstance(data, list):
            valid, failed = [], 0
            for item in data:
                try:
                    parsed = (
                        item
                        if isinstance(item, TaskExtraction)
                        else TaskExtraction.model_validate(item)
                    )
                    valid.append(parsed)
                except (ValidationError, Exception):
                    failed += 1
            return {"tasks": valid, "failed_items": failed}
        return data


class StatusExtractionList(BaseModel):
    """
    Fault-tolerant wrapper для ответа status_chain.

    Аналогично TaskExtractionList: per-item валидация,
    один сбойный элемент не роняет остальные.
    """
    statuses: list[StatusExtraction] = Field(default_factory=list)
    failed_items: int = Field(default=0, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_raw_list(cls, data: Any) -> dict:
        """Принимает и список [{...}] и словарь {"statuses": [...]} — оба формата."""
        if isinstance(data, list):
            valid, failed = [], 0
            for item in data:
                try:
                    parsed = (
                        item
                        if isinstance(item, StatusExtraction)
                        else StatusExtraction.model_validate(item)
                    )
                    valid.append(parsed)
                except (ValidationError, Exception):
                    failed += 1
            return {"statuses": valid, "failed_items": failed}
        return data
