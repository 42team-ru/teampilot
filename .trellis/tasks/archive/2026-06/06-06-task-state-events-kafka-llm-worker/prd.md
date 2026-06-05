# task-state-events: Kafka события при всех изменениях задач

## Goal

Публиковать события при каждом изменении состояния задачи в два разных топика:
- **`tasks.state`** → бот (уведомления в Telegram-чат)
- **`tasks.lifecycle`** → LLM Worker (синхронизация Qdrant)

## Текущее состояние

Из 7 точек изменения состояния задачи только 2 публикуют в Kafka:
- `TaskService.createFromLlmEvent` (auto-confirm) → `bots.tasks` ✅
- `TaskService.approve()` → `bots.tasks` ✅

Не покрыты:
- `createFromLlmEvent` → PENDING_APPROVAL (не нужно боту)
- `cancel()` → DELETED_FROM_YOUGILE
- `updateFromLlmEvent()` → колонка / assignee / title / DELETED
- `YouGileBoardSyncService.updateTask()` → колонка / title / description / deadline
- `YouGileBoardSyncService.importTask()` → новая задача из YouGile

## Топики

### `tasks.state` (Spring → Bot)
Формат: `TaskStateEvent` с полями:
- `taskId` (UUID)
- `chatId` (Long) — для роутинга боту
- `type` (enum): CREATED, CANCELLED, COLUMN_CHANGED, IMPORTED, UPDATED
- `title` (String)
- `columnTitle` (String, nullable) — новая колонка
- `assigneeUsername` (String, nullable)
- `deadline` (Instant, nullable)

### `tasks.lifecycle` (Spring → LLM Worker)
Формат: `TaskLifecycleEvent` с полями:
- `taskId` (UUID)
- `teamId` (UUID)
- `type` (enum): CONFIRMED, CANCELLED
- `title` (String)
- `description` (String)

LLM Worker при CONFIRMED → `store_task()` в Qdrant
LLM Worker при CANCELLED → `delete` из Qdrant

## Открытые вопросы

(нет)

## Решение: что слать в бот

- **CREATED** (approve / auto-confirm / import из YouGile)
- **COLUMN_CHANGED** (смена статуса — колонка сдвинулась)
- **CANCELLED** (удалена)
- title/description/deadline изменения → тихо, не слать в бот

## Technical Notes

- `AbstractEventPublisher` + `KafkaTopics` — существующий паттерн
- Bot слушает: `tasks.propose`, `reminders.send`, `summary.send`
- LLM Worker: нужен новый Kafka consumer в `main.py` + восстановить `infra/qdrant.py` (минимально: `store_task`, `delete_task`)
- Файлы Spring: `TaskService.java`, `YouGileBoardSyncService.java`, `TaskEventPublisher.java`, `KafkaTopics.java`
- Файлы LLM Worker: `main.py`, `infra/qdrant.py` (новый)
- Файлы Bot: `kafka/consumer.py`, `kafka/topics.py`, `models/events.py`
