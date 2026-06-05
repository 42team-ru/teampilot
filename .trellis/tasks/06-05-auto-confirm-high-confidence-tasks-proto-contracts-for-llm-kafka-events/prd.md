# Auto-confirm high-confidence tasks + proto contracts for LLM Kafka events

## Goal

Убрать лишний шаг подтверждения для задач, в которых LLM уверена: если `confidence >= AUTO_CONFIRM_THRESHOLD` — задача сразу создаётся в YouGile, бот присылает уведомление с кнопкой «Отменить». Спорные задачи (confidence ниже порога) идут по старому пути через ✅/✏️/❌ менеджера. Параллельно — вынести Kafka-контракты `llm.tasks.create` и `llm.status.change` в `.proto`-файлы (как уже сделано для `messages.batches`).

## Requirements

1. `AUTO_CONFIRM_THRESHOLD: float = 0.90` — новая env-переменная в `settings.py`
2. `TaskCreateEvent` (LLM → Spring) получает поле `confidence: float`
3. В `processor.py` `confidence_task` из `ClassificationResult` передаётся в каждый `TaskCreateEvent`
4. Spring: `createFromLlmEvent` — если `confidence >= AUTO_CONFIRM_THRESHOLD`:
   - сразу `TaskLocalStatus.ACTIVE`
   - вызов YouGile API для создания карточки
   - публикация `TaskConfirmationEvent` с `autoConfirmed = true`
5. Spring: если `confidence < threshold` — прежний flow (`PENDING_APPROVAL`, кнопки ✅/✏️/❌)
6. `TaskConfirmationEvent` получает поле `autoConfirmed: boolean`; бот рисует только «Отменить» при `autoConfirmed=true`
7. Новый endpoint `POST /tasks/{id}/cancel` (роль BOT или SYSTEM_ADMIN):
   - вызывает YouGile API delete
   - ставит `TaskLocalStatus.DELETED_FROM_YOUGILE` локально
8. `llm.tasks.create` сериализуется через Protobuf (новый `task_create.proto`)
9. `llm.status.change` сериализуется через Protobuf (новый `status_change.proto`)
10. Python llm-worker публикует оба топика через сгенерированные pb2-классы
11. Java consumer `LlmTaskCreateConsumer` десериализует через proto

## Acceptance Criteria

- [ ] Задача с `confidence=0.95` создаётся в YouGile без нажатия кнопок; бот присылает «Создана: X [Отменить]»
- [ ] Задача с `confidence=0.70` остаётся `PENDING_APPROVAL`; менеджер видит ✅/✏️/❌
- [ ] `POST /tasks/{id}/cancel` удаляет из YouGile и ставит `DELETED_FROM_YOUGILE` локально
- [ ] `llm.tasks.create` использует proto-сериализацию на Python- и Java-стороне
- [ ] `llm.status.change` использует proto-сериализацию на Python-стороне
- [ ] Новые `.proto`-файлы лежат в `kafka-proto-common/src/main/proto/`
- [ ] `proto_generated/` в llm-worker обновлён

## Decision (ADR-lite)

**Context**: Все задачи шли через `PENDING_APPROVAL`; менеджер тратил время на подтверждение очевидных задач.

**Decision**: Порог auto-confirm как env-переменная (0.90 по умолчанию). Отмена auto-confirmed задачи удаляет из YouGile. Уведомление через существующий `TaskConfirmationEvent` + флаг `autoConfirmed`. Kafka-контракты LLM → Spring в proto (как `messages.batches`).

**Consequences**: Меньше ручной работы для PM; при отмене задача исчезает из YouGile безвозвратно (история в локальной БД сохраняется через `DELETED_FROM_YOUGILE`).

## Out of Scope

- Перевод `bots.tasks` и `bots.notifications` в proto
- Кнопка «Редактировать» при auto-confirm (только «Отменить»)
- Перевод `audio.transcript.ready` в proto
- Порог auto-confirm на уровне команды (в БД)

## Technical Notes

### Файлы к изменению — LLM Worker
- `llm-worker/settings.py` — `AUTO_CONFIRM_THRESHOLD: float = 0.90`
- `llm-worker/models.py` — `TaskCreateEvent.confidence: float = 0.0`
- `llm-worker/processor.py` — передавать `clf.confidence_task` в `TaskCreateEvent`
- `llm-worker/infra/kafka.py` — переключить publish на proto для `llm.tasks.create` и `llm.status.change`
- `llm-worker/proto_generated/` — регенерировать с новыми proto

### Файлы к изменению — Backend
- `kafka-proto-common/src/main/proto/ru/team42/events/task_create.proto` — новый
- `kafka-proto-common/src/main/proto/ru/team42/events/status_change.proto` — новый
- `monolith/event/LlmTaskCreateEvent.java` — добавить `confidence: float`
- `monolith/event/TaskConfirmationEvent.java` — добавить `autoConfirmed: boolean`
- `monolith/service/TaskService.java` — ветка auto-confirm в `createFromLlmEvent` + метод `cancelAutoConfirmed`
- `monolith/service/TaskEventPublisher.java` — передавать `autoConfirmed` флаг
- `monolith/rest/TaskController.java` — `POST /tasks/{id}/cancel`
- `monolith/kafka/consumer/LlmTaskCreateConsumer.java` — proto-десериализация

### Существующий proto
- `kafka-proto-common/src/main/proto/ru/team42/events/message_batch.proto` — образец структуры
- `llm-worker/proto_generated/ru/team42/events/message_batch_pb2.py` — образец генерации

### Поля proto (draft)
```proto
// task_create.proto
message LlmTaskCreateEvent {
  string team_id = 1;
  string title = 2;
  string description = 3;
  string assignee = 4;
  int64 assignee_id = 5;
  string deadline = 6;        // ISO string
  string priority = 7;        // HIGH/MEDIUM/LOW
  string column_id = 8;
  string source_batch_id = 9;
  float confidence = 10;
}

// status_change.proto
message LlmStatusChangeEvent {
  string team_id = 1;
  string task_hint = 2;
  string assignee = 3;
  int64 assignee_id = 4;
  string action = 5;          // COMPLETE/ASSIGN/CANCEL
  string source_batch_id = 6;
  string resolved_task_id = 7;
}
```
