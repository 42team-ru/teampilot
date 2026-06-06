from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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


class TaskStateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    task_id: str = Field(alias="taskId")
    chat_id: int = Field(alias="chatId")
    type: Literal["CREATED", "CANCELLED", "COLUMN_CHANGED"]
    title: str
    column_title: str | None = Field(default=None, alias="columnTitle")
    assignee_username: str | None = Field(default=None, alias="assigneeUsername")
    deadline: datetime | None = None


class BackendEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class BotNotificationEvent(BackendEvent):
    telegram_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("telegramId", "telegram_id"),
    )
    chat_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("chatId", "chat_id"),
    )
    type: str
    task_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("taskId", "task_id"),
    )
    task_title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("taskTitle", "task_title"),
    )


class TaskConfirmationEvent(BackendEvent):
    task_id: str = Field(validation_alias=AliasChoices("taskId", "task_id"))
    chat_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("chatId", "chat_id"),
    )
    title: str
    description: str | None = None
    assignee_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("assigneeUsername", "assignee_username"),
    )
    deadline: datetime | None = None
    auto_confirmed: bool = Field(
        default=False,
        validation_alias=AliasChoices("autoConfirmed", "auto_confirmed"),
    )
