from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# ── Kafka: Spring → LLM Worker ─────────────────────────────────────────────

class MessageDto(BaseModel):
    user_id: int
    username: str | None = None
    full_name: str
    text: str
    timestamp: datetime


class MessageBatchEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    chat_id: int
    messages: list[MessageDto]
    batch_start: datetime
    batch_end: datetime


# ── Kafka: LLM Worker → Spring ──────────────────────────────────────────────

class TaskCreateEvent(BaseModel):
    chat_id: int
    title: str
    description: str
    assignee: str | None = None
    deadline: str | None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    source_batch_id: str


class StatusChangeEvent(BaseModel):
    chat_id: int
    task_hint: str
    assignee: str | None = None
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
