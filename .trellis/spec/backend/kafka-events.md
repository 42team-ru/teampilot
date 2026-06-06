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
| CONFIRMED | `store_task(task_id, title, description, team_id)` — upsert searchable task points |
| UPDATED | same as CONFIRMED — upsert replaces searchable task points |
| CANCELLED | `delete_task(task_id)` — removes old single-point IDs and all searchable task points |

`store_task` does not write one Qdrant point per task anymore. It writes
multiple stable point IDs for different searchable representations of the same
task, then `search_tasks(...)` aggregates Qdrant hits back to unique task
candidates.

### 4. LLM Worker Task Search Index Contract

#### Scope / Trigger

Triggered by Spring `tasks.lifecycle` events. The LLM Worker uses this index
for duplicate detection and for status-change candidate retrieval before asking
the LLM to choose a `task_id`.

#### Signatures

```python
store_task(task_id: str, title: str, description: str, team_id: str) -> None
delete_task(task_id: str) -> None
search_tasks(
    query: str,
    team_id: str,
    limit: int = 5,
    score_threshold: float | None = None,
) -> list[dict]
is_task_duplicate(title: str, description: str, team_id: str) -> bool
```

#### Contracts

Task points are written to `settings.QDRANT_COLLECTION_TASKS` with:

| Payload field | Type | Notes |
|---|---|---|
| `task_id` | string | Local DB task UUID from Spring |
| `team_id` | string | Required filter for every query |
| `title` | string | Normalized task title |
| `description` | string | Normalized description; service confidence lines are removed |
| `kind` | string | One of `summary`, `title`, `description`, `status` |
| `text` | string | Exact text embedded for this representation |

Point IDs are deterministic UUIDv5 values derived from `task_id + kind`. Keep
the old raw `task_id` in the delete selector so cancellations clean up points
written by the previous single-vector implementation.

`search_tasks(...)` must:
- embed the normalized query;
- filter by `team_id`;
- query more Qdrant points than the requested candidate limit;
- apply `settings.STATUS_HINT_THRESHOLD` when no explicit score threshold is
  provided;
- aggregate multiple hits for the same `task_id`;
- return unique task candidates with `task_id`, `title`, `description`, `score`,
  `matched_kind`, `matched_text`, and `matches`.

Before status-change extraction calls `search_tasks(...)`, it must build
focused search queries from status-like chat messages or transcript snippets.
Do not embed the entire formatted message batch as the status lookup query; it
mixes unrelated lunch/noise/new-task text into the vector and makes Qdrant return
weak candidates.

`is_task_duplicate(...)` must use `settings.DEDUP_THRESHOLD`, not
`STATUS_HINT_THRESHOLD`.

#### Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Empty query | Return `[]` without calling Qdrant |
| Embedding provider fails | Log `warning`, return safe fallback (`[]` / `False`) |
| Qdrant query/upsert/delete fails | Log `warning`, do not crash Kafka consumer |
| Missing payload `task_id` in a Qdrant hit | Ignore that hit |
| Multiple hits for same task | Aggregate to one candidate and keep match metadata |
| No status-like query can be extracted | Return no task candidates; the LLM may still output `task_id = null` |

#### Good/Base/Bad Cases

- Good: query `"qdrant готов"` matches a task title plus status representation
  and returns one candidate with two matches.
- Good: formatted batch with lunch/noise plus `"авторизацию закрыл"` searches
  Qdrant using `"авторизацию закрыл"`, not the full batch.
- Base: an old single-point task still has only `task_id`, `title`, `team_id`;
  aggregation still returns a usable candidate.
- Bad: a low-score unrelated task should be filtered out by
  `STATUS_HINT_THRESHOLD` instead of being shown to the status prompt.

#### Tests Required

- `store_task` writes multiple points with stable UUID point IDs and cleaned
  descriptions.
- `search_tasks` aggregates multiple points for the same task and preserves
  match metadata.
- `delete_task` includes both old raw task ID and all derived point IDs.
- `is_task_duplicate` passes `DEDUP_THRESHOLD`.
- Status prompt formatting includes retrieval context, not only task title.
- Status candidate lookup calls Qdrant once per focused status query and does
  not use unrelated batch messages as vector query input.

#### Wrong vs Correct

Wrong:
```python
PointStruct(
    id=task_id,
    vector=embed(f"{title}\n{description}"),
    payload={"task_id": task_id, "title": title, "team_id": team_id},
)
```

Correct:
```python
PointStruct(
    id=uuid5(namespace, f"{task_id}:{kind}"),
    vector=embed(representation_text),
    payload={
        "task_id": task_id,
        "team_id": team_id,
        "title": title,
        "description": description,
        "kind": kind,
        "text": representation_text,
    },
)
```

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
