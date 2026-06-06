# Kafka Event Contracts

> Cross-layer contracts for Kafka events between Spring (producer) and Python consumers (Bot, LLM Worker).

---

## Serialization: Spring → Python

### Critical Gotcha: Spring serializes camelCase, Python must use aliases

Spring's `JsonMapper` (Jackson) serializes field names in **camelCase** by default.
Python Pydantic models that consume these events **must** declare `Field(alias=...)` for every camelCase field, plus `ConfigDict(populate_by_name=True)`.

**Wrong** — silent parse failure, fields come back as `None`:
```python
class TaskStateEvent(BaseModel):
    task_id: str
    chat_id: int
    column_title: str | None = None
```

**Correct**:
```python
class TaskStateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(alias="taskId")
    chat_id: int = Field(alias="chatId")
    column_title: str | None = Field(default=None, alias="columnTitle")
```

The exception is `KafkaConsumerConfig` on the Spring side which uses `SNAKE_CASE` strategy for **inbound** events (LLM Worker → Spring direction). That affects only `messages.batches`, `llm.tasks.create`, `llm.status.change`.

---

## Topic Architecture

| Topic | Producer | Consumers | Purpose |
|---|---|---|---|
| `tasks.state` | Spring | Bot | Task DM notifications (CREATED / UPDATED / COLUMN_CHANGED / CANCELLED) |
| `tasks.lifecycle` | Spring | LLM Worker | Qdrant sync (CONFIRMED / UPDATED / CANCELLED) |
| `bots.tasks` | Spring | Bot | Confirmed task DM notifications |
| `bots.notifications` | Spring | Bot | Scheduled task DM notifications (deadline / stale) |
| `messages.batches` | Spring | LLM Worker | Batches for LLM analysis |
| `llm.tasks.create` | LLM Worker | Spring | Create task from LLM |
| `llm.status.change` | LLM Worker | Spring | Status change from LLM |

---

## Scenario: Task State Events (tasks.state)

### 1. Scope / Trigger

Sent by Spring at task mutations that should be visible to users in bot direct messages. Task notifications must not be posted into team group chats.

Recipient routing is resolved on the Spring side:
- managers receive every task notification for their teams
- if a task has an assignee, the assignee also receives the notification
- if a task has no assignee, all team members receive the notification
- duplicate Telegram IDs are removed before publishing

### 2. Signatures

**Java producer** (`TaskEventPublisher`):
```java
public void publishCreated(Task task)       // → CREATED + CONFIRMED (lifecycle)
public void publishCancelled(Task task)     // → CANCELLED + CANCELLED (lifecycle)
public void publishColumnChanged(Task task, TaskColumn newColumn)  // → COLUMN_CHANGED
public void publishUpdated(Task task)       // → UPDATED + UPDATED (lifecycle)
```

**Python consumer** (`bot/models/events.py`):
```python
class TaskStateEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    task_id: str = Field(alias="taskId")
    recipient_telegram_ids: list[int] = Field(alias="recipientTelegramIds")
    type: Literal["CREATED", "UPDATED", "CANCELLED", "COLUMN_CHANGED"]
    title: str
    column_title: str | None = Field(default=None, alias="columnTitle")
    assignee_username: str | None = Field(default=None, alias="assigneeUsername")
    deadline: datetime | None = None
```

### 3. Contracts

All events extend `BaseEvent` which adds `eventId: UUID` and `occurredAt: Instant`.

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `taskId` | UUID | no | Local DB task ID |
| `recipientTelegramIds` | long[] | no | DM recipients; resolved from managers + assignee/all-members rule |
| `type` | enum | no | CREATED / UPDATED / COLUMN_CHANGED / CANCELLED |
| `title` | String | no | |
| `columnTitle` | String | yes | null for CANCELLED |
| `assigneeUsername` | String | yes | Telegram @username |
| `deadline` | Instant | yes | ISO-8601 UTC |

### 4. Mutation Points → Publisher Calls

| Method | Event(s) emitted |
|---|---|
| `TaskService.createFromLlmEvent` (auto-confirm) | CREATED + CONFIRMED |
| `TaskService.approve()` | CREATED + CONFIRMED |
| `TaskService.cancel()` | CANCELLED + CANCELLED |
| `TaskService.updateFromLlmEvent()` deleted=true | CANCELLED + CANCELLED |
| `TaskService.updateFromLlmEvent()` details changed | UPDATED |
| `TaskService.updateFromLlmEvent()` column changed | COLUMN_CHANGED |
| `YouGileBoardSyncService.importTask()` | CREATED + CONFIRMED |
| `YouGileBoardSyncService.updateTask()` column changed | COLUMN_CHANGED |
| `YouGileBoardSyncService.updateTask()` title/desc/deadline/assignee changed | UPDATED |

### 5. Good/Base/Bad Cases

- **Good**: task created with assignee and deadline → managers and assignee receive a DM with all fields
- **Base**: task created, no assignee/deadline → all team members receive a DM with "не указан"
- **Bad**: no team members have Telegram IDs → notification is skipped and logged; group chat fallback is forbidden

---

## Scenario: Task Lifecycle Events (tasks.lifecycle)

### 1. Scope / Trigger

Consumed by LLM Worker for Qdrant upsert/delete. Silent — no bot notification.

### 2. Python model

```python
class TaskLifecycleEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    task_id: str = Field(alias="taskId")
    team_id: str = Field(alias="teamId")
    type: Literal["CONFIRMED", "UPDATED", "CANCELLED"]
    title: str
    description: str | None = None
```

### 3. Qdrant Actions

| type | Qdrant action |
|---|---|
| CONFIRMED | `store_task(task_id, title, description, team_id)` — upsert |
| UPDATED | same as CONFIRMED — upsert replaces embedding |
| CANCELLED | `delete_task(task_id)` |

`store_task` uses Qdrant's `add()` which is an **upsert by point ID**. Calling it again with the same `task_id` but updated text replaces the embedding.

---

## YouGile Epoch Format

YouGile API expects **milliseconds**, not seconds.

```java
// Wrong — sends epoch seconds (shows as 1970):
dl.setDeadline(BigDecimal.valueOf(task.getDeadline().getEpochSecond()));

// Correct:
dl.setDeadline(BigDecimal.valueOf(task.getDeadline().toEpochMilli()));
```

Also never use `getSecond()` (returns second-of-minute, 0–59) for timestamps.

When reading back from YouGile:
```java
// Wrong:
return Instant.ofEpochSecond(d.getDeadline().longValue());
// Correct:
return Instant.ofEpochMilli(d.getDeadline().longValue());
```
