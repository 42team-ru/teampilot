# batch-task-state-notifications

## Goal

При массовых действиях (отмена/перемещение нескольких задач) бот шлёт отдельное сообщение на каждое событие. Нужно батчить `TaskStateEvent` по типу аналогично тому, как уже батчатся `TaskConfirmationEvent`.

## What I already know

* `consumer.py` уже батчит `BOTS_TASKS` (TaskConfirmationEvent): `_queue_confirmation` + `_flush_confirmations` с 3-секундным окном, group by `chat_id`
* `TASKS_STATE` → `_send_task_state` — никакого батчинга, каждое событие = отдельное сообщение
* Типы TaskStateEvent: `CREATED` (игнорируется ботом), `CANCELLED`, `COLUMN_CHANGED`
* `_BATCH_WINDOW_SECS = 3` — константа уже есть

## Requirements

* `CANCELLED` события батчатся по `chat_id`, окно 3 сек
* `COLUMN_CHANGED` события батчатся по `chat_id`, окно 3 сек
* Одно событие (N=1) — тот же формат что сейчас
* N>1 CANCELLED → одно сообщение вида "❌ Отменено задач: N\n1. Title\n2. Title..."
* N>1 COLUMN_CHANGED → одно сообщение вида "🔄 Перемещено задач: N\n1. Title → Колонка\n2. ..."

## Acceptance Criteria

* [ ] 5 CANCELLED подряд → 1 сообщение со списком
* [ ] 1 CANCELLED → прежний формат (одно сообщение с заголовком)
* [ ] COLUMN_CHANGED батчится аналогично
* [ ] CREATED по-прежнему игнорируется

## Technical Approach

Добавить в `EventConsumer`:
- `_pending_states: dict[int, list[TaskStateEvent]]`
- `_state_flush: dict[int, asyncio.Task]`
- метод `_queue_state(bot, event)` — кладёт в pending, стартует flush-таску если нет
- метод `_flush_states(bot, chat_id)` — ждёт 3 сек, group by type, форматирует и шлёт
- В `_dispatch`: `TASKS_STATE` + type != CREATED → `_queue_state`

## Out of Scope

* Изменение Java-стороны
* Батчинг других топиков

## Technical Notes

* Файл: `bot/kafka/consumer.py`
* Паттерн батчинга взят из `_queue_confirmation` / `_flush_confirmations`
