from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# Outgoing: Bot → Backend

class RawMessageEvent(BaseModel):
    message_id: int
    chat_id: int
    user_id: int
    username: str | None
    full_name: str
    text: str
    timestamp: datetime


class AudioUploadEvent(BaseModel):
    user_id: int
    chat_id: int
    minio_key: str
    file_name: str
    duration: int | None
    timestamp: datetime


class FileUploadedEvent(BaseModel):
    user_id: int
    chat_id: int
    username: str | None
    first_name: str | None
    original_filename: str
    content_type: str
    minio_bucket: str
    minio_key: str
    file_size: int
    uploaded_at: datetime


class TaskConfirmedEvent(BaseModel):
    proposal_id: str
    user_id: int
    chat_id: int


class TaskRejectedEvent(BaseModel):
    proposal_id: str
    user_id: int


class StatusChangedEvent(BaseModel):
    task_id: str
    user_id: int
    new_status: str  # "in_progress" | "done" | "blocked"


# Incoming: Backend → Bot

class TaskProposeEvent(BaseModel):
    proposal_id: str
    chat_id: int
    task_title: str
    assignee_name: str | None
    deadline: datetime | None
    source: str  # "chat" | "meeting"


class ReminderSendEvent(BaseModel):
    user_id: int
    chat_id: int | None  # None → send to user DM
    text: str
    task_id: str | None


class SummarySendEvent(BaseModel):
    chat_id: int
    summary_text: str
    tasks_count: int
