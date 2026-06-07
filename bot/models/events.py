from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


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

class TaskStateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    task_id: str = Field(alias="taskId")
    chat_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("chatId", "chat_id"),
    )
    recipient_telegram_ids: list[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipientTelegramIds", "recipient_telegram_ids"),
    )
    type: Literal["CREATED", "UPDATED", "CANCELLED", "COLUMN_CHANGED"]
    title: str
    column_title: str | None = Field(default=None, alias="columnTitle")
    assignee_username: str | None = Field(default=None, alias="assigneeUsername")
    deadline: datetime | None = None


class BackendEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class BotNotificationEvent(BackendEvent):
    recipient_telegram_ids: list[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipientTelegramIds", "recipient_telegram_ids"),
    )
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
    achievement_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("achievementName", "achievement_name"),
    )
    achievement_emoji: str | None = Field(
        default=None,
        validation_alias=AliasChoices("achievementEmoji", "achievement_emoji"),
    )
    xp_gained: int | None = Field(
        default=None,
        validation_alias=AliasChoices("xpGained", "xp_gained"),
    )
    new_total_xp: int | None = Field(
        default=None,
        validation_alias=AliasChoices("newTotalXp", "new_total_xp"),
    )
    new_level_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("newLevelName", "new_level_name"),
    )
    courses: list[dict] | None = Field(default=None)
    meeting_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("meetingId", "meeting_id"),
    )
    meeting_title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("meetingTitle", "meeting_title"),
    )
    meeting_summary: str | None = Field(
        default=None,
        validation_alias=AliasChoices("meetingSummary", "meeting_summary"),
    )
    meeting_tasks: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("meetingTasks", "meeting_tasks"),
    )
    meeting_hints: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("meetingHints", "meeting_hints"),
    )
    meeting_speakers: list[dict] = Field(
        default_factory=list,
        validation_alias=AliasChoices("meetingSpeakers", "meeting_speakers"),
    )


class SyncDraftItem(BackendEvent):
    index: int
    user_text: str = Field(validation_alias=AliasChoices("userText", "user_text"))
    task_id: str | None = Field(default=None, validation_alias=AliasChoices("taskId", "task_id"))
    task_title: str | None = Field(default=None, validation_alias=AliasChoices("taskTitle", "task_title"))
    is_new_task: bool = Field(default=False, validation_alias=AliasChoices("isNewTask", "is_new_task"))
    assignee_telegram_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("assigneeTelegramId", "assignee_telegram_id"),
    )
    assignee_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("assigneeName", "assignee_name"),
    )


class SyncSummary(BackendEvent):
    responded_usernames: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("respondedUsernames", "responded_usernames"),
    )
    not_responded_usernames: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("notRespondedUsernames", "not_responded_usernames"),
    )
    tasks_completed: int = Field(default=0, validation_alias=AliasChoices("tasksCompleted", "tasks_completed"))
    new_tasks_pending_approval: int = Field(
        default=0,
        validation_alias=AliasChoices("newTasksPendingApproval", "new_tasks_pending_approval"),
    )
    excused_entries: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("excusedEntries", "excused_entries"),
    )


class BotSyncEvent(BackendEvent):
    type: str
    chat_id: int | None = Field(default=None, validation_alias=AliasChoices("chatId", "chat_id"))
    recipient_telegram_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("recipientTelegramId", "recipient_telegram_id"),
    )
    recipient_telegram_ids: list[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipientTelegramIds", "recipient_telegram_ids"),
    )
    draft: list[SyncDraftItem] = Field(default_factory=list)
    summary: SyncSummary | None = None

    @field_validator("draft", "recipient_telegram_ids", mode="before")
    @classmethod
    def _coerce_list(cls, v: object) -> object:
        return v if v is not None else []


class TaskConfirmationEvent(BackendEvent):
    task_id: str | None = Field(default=None, validation_alias=AliasChoices("taskId", "task_id"))
    proposal_id: str | None = Field(default=None, validation_alias=AliasChoices("proposalId", "proposal_id"))
    chat_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("chatId", "chat_id"),
    )
    recipient_telegram_ids: list[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recipientTelegramIds", "recipient_telegram_ids"),
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
    column_title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("columnTitle", "column_title"),
    )
