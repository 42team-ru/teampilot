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

The exception is `KafkaConsumerConfig` on the Spring side which uses `SNAKE_CASE` strategy for **inbound** events (LLM Worker → Spring direction), for example `llm.tasks.create`, `llm.status.change`, `files.transcript_ready`, and `meetings.live.results`.

---

## Topic Architecture

| Topic | Producer | Consumers | Purpose |
|---|---|---|---|
| `tasks.state` | Spring | Bot | Task DM notifications (CREATED / UPDATED / COLUMN_CHANGED / CANCELLED) |
| `tasks.lifecycle` | Spring | LLM Worker | Qdrant sync (CONFIRMED / UPDATED / CANCELLED) |
| `bots.tasks` | Spring | Bot | Confirmed task DM notifications |
| `bots.notifications` | Spring | Bot | Scheduled task DM notifications (deadline / stale) |
| `messages.batches` | Spring | LLM Worker | Batches for LLM analysis |
| `audio.new` | Spring | LLM Worker | Uploaded audio/video file transcription |
| `llm.tasks.create` | LLM Worker | Spring | Create task from LLM |
| `llm.status.change` | LLM Worker | Spring | Status change from LLM |
| `files.transcript_ready` | LLM Worker | Spring | File summary after audio transcription |
| `meetings.audio.chunks` | Spring | LLM Worker | Live meeting audio chunks stored in MinIO |
| `meetings.live.results` | LLM Worker | Spring | Live transcript/task/status/summary payload for WebSocket broadcast |

---

## Scenario: Live Meeting Audio Events

### 1. Scope / Trigger

Triggered when a team manager creates a `Meeting` and the meeting's primary
recorder sends audio chunks over Spring WebSocket/STOMP. Spring stores every
accepted chunk in MinIO and emits `meetings.audio.chunks`; the LLM Worker
transcribes the chunk, maintains an in-memory sliding transcript context per
meeting, publishes normal `llm.tasks.create` / `llm.status.change` events for
mutations, then publishes `meetings.live.results` so Spring can broadcast live
updates to `/topic/meetings/{meetingId}/results`. When `finalChunk=true`, the
LLM Worker also uploads a final recording and full transcript to MinIO and sends
their object fields in the same `meetings.live.results` event.

### 2. Signatures

**Java producer** (`MeetingAudioChunkPublisher`):
```java
public void publishChunk(
    Meeting meeting,
    int chunkIndex,
    boolean finalChunk,
    String bucket,
    String s3Key,
    String originalFilename,
    String contentType,
    long sizeBytes
)
```

**Python consumer** (`llm-worker/models.py`):
```python
class MeetingAudioChunkEvent(BaseModel):
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
```

**Python producer** (`MeetingLiveResultEvent`) → Spring consumer
(`MeetingLiveResultConsumer`):
```python
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
```

### 3. Contracts

`meetings.audio.chunks` is Spring → Python and therefore serializes fields as
camelCase. Python must use Pydantic aliases for all multi-word fields.

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `meetingId` | string UUID | no | Local DB meeting ID |
| `teamId` | string UUID | no | Team scope for task extraction and Qdrant status lookup |
| `recorderTelegramId` | long | yes | Primary recorder Telegram ID |
| `chunkIndex` | int | no | Client-provided monotonically increasing chunk number |
| `finalChunk` | boolean | no | Forces extraction even if context threshold is not reached |
| `bucket` | string | no | MinIO bucket containing this chunk |
| `s3Key` | string | no | MinIO object key, under `meetings/{meetingId}/chunks/` |
| `originalFilename` | string | no | Used as Whisper filename hint |
| `contentType` | string | no | Defaults to `audio/webm` at the Spring boundary |
| `team` / `columns` / `stickers` | arrays | no | Same context shape as `audio.new` |

`meetings.live.results` is Python → Spring and therefore sends snake_case JSON.
Spring's `KafkaConsumerConfig` maps it to camelCase Java fields.
The LLM Worker may process different meetings in parallel. Live transcript
context is in-memory and best-effort, but `finalChunk=true` recording
finalization must use durable MinIO state, not `_meeting_state`. List objects
under `meetings/{meetingId}/chunks/`, wait up to `MEETING_FINALIZE_WAIT_SECONDS`
for chunk indexes `0..chunkIndex`, then finalize with available chunks rather
than blocking all meetings globally.

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `meeting_id` | string UUID | no | Broadcast destination key |
| `team_id` | string UUID | no | Team scope |
| `chunk_index` | int | no | Chunk that produced this result |
| `transcript` | string | no | Whisper text for this chunk |
| `summary` | string | no | Empty when no extraction ran for this chunk |
| `context` | string | no | Sliding transcript window currently used by LLM |
| `final_result` | boolean | no | True only for successfully finalized meeting output |
| `title` | string | yes | Final meeting title from full transcript |
| `description` | string | yes | Final meeting description from full transcript |
| `recording_bucket` | string | yes | MinIO bucket for final recording |
| `recording_s3_key` | string | yes | `meetings/{meetingId}/final/recording.mp3` or fallback `.webm` |
| `recording_content_type` | string | yes | Usually `audio/mpeg`, fallback `audio/webm` |
| `recording_size_bytes` | int | yes | Final recording object size |
| `transcript_bucket` | string | yes | MinIO bucket for final transcript |
| `transcript_s3_key` | string | yes | `meetings/{meetingId}/final/transcript.txt` |
| `finalized_at` | ISO-8601 datetime | yes | When final recording/transcript were produced |
| `tasks` | array | no | Preview of newly extracted task events |
| `statuses` | array | no | Preview of newly extracted status-change events |

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| WebSocket sender is not authenticated | Reject the STOMP message |
| Sender is not a member of the meeting team | Reject with forbidden |
| Sender is not `Meeting.primaryRecorder` | Reject with forbidden; do not store or publish the chunk |
| `audioBase64` is invalid or empty | Reject before S3 upload |
| MinIO upload fails | Do not publish `meetings.audio.chunks` |
| LLM Worker cannot download/transcribe chunk | Log error, commit Kafka message, no live result |
| Context has not reached extraction threshold | Publish live transcript result with empty `tasks`/`statuses` |
| `finalChunk=true` | Run extraction even below the normal threshold; merge chunks; upload final recording and transcript; update `Meeting` final fields in Spring |

### 5. Good/Base/Bad Cases

- **Good**: manager creates meeting, sends chunks `0..N`, worker publishes transcript results and only new task/status previews; Spring broadcasts to all subscribers.
- **Good**: final chunk uploads `recording.mp3` and `transcript.txt`, then `GET /meetings/by-url` exposes final `recording*`, `transcript*`, `title`, `description`, `summary`.
- **Base**: short chunk has useful transcript but not enough context; subscribers still see transcript, task extraction waits for more context.
- **Bad**: two participants send duplicated audio; only the primary recorder's chunks are accepted, preventing duplicate MinIO objects and repeated LLM extraction.

### 6. Tests Required

User explicitly requested no tests for the initial implementation. If tests are
added later, cover:

- manager-only `POST /meetings`;
- non-primary recorder STOMP chunk rejection;
- `meetings.audio.chunks` payload aliases in Python;
- `meetings.live.results` snake_case deserialization in Spring;
- final chunk forcing extraction below threshold.
- final chunk storing final recording/transcript keys and summary fields on `Meeting`.

### 7. Wrong vs Correct

#### Wrong
```python
class MeetingAudioChunkEvent(BaseModel):
    meeting_id: str
    s3_key: str
```
Spring sends `meetingId` and `s3Key`, so these fields parse as missing.

#### Correct
```python
class MeetingAudioChunkEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    meeting_id: str = Field(alias="meetingId")
    s3_key: str = Field(alias="s3Key")
```

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
