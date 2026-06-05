# loadColumns: использовать TaskColumn из Postgres вместо YouGile API

## Goal

`ChatMessageBatchingService#loadColumns` сейчас вызывает YouGile HTTP API на каждый flush батча.
Заменить на `taskColumnRepository.findByTeamId(team.getId())` — Postgres быстрее, надёжнее, и TaskColumn — источник правды.

## Decision

`ColumnDto.id` = `TaskColumn.id` (UUID из Postgres), **не** `youGileColumnId`.

Почему: TaskColumn — источник правды. LLM возвращает UUID → Spring делает `taskColumnRepository.findById(columnId)` → получает `youGileColumnId` → вызывает YouGile. Это отвязывает LLM worker от YouGile полностью.

## Requirements

- `loadColumns` → `taskColumnRepository.findByTeamId(team.getId())`
- `ColumnDto.id` = `taskColumn.getId().toString()`
- `ChatMessageBatchPublisher#toProtoColumn` — без изменений (берёт `col.id()`)
- `TaskService` (или где создаётся задача в YouGile): при получении `LlmTaskCreateEvent.columnId` делать lookup `taskColumnRepository.findById(UUID.fromString(columnId))` → использовать `youGileColumnId`
- **Не добавлять** `@OneToMany List<TaskColumn> columns` в `Team` — `TaskColumnRepository.findByTeamId` достаточно

## Acceptance Criteria

- [ ] `loadColumns` не делает HTTP-запрос к YouGile
- [ ] `ColumnDto.id` = UUID из `task_columns` таблицы
- [ ] Задача создаётся в YouGile с корректным `youGileColumnId`
- [ ] Компиляция чистая

## Out of Scope

- Синхронизация колонок (YouGileBoardSyncService — отдельный таск)
- Добавление новых колонок через API

## Technical Notes

Файлы:
- `backend/monolith/src/.../service/ChatMessageBatchingService.java` — метод `loadColumns`
- `backend/monolith/src/.../service/ChatMessageBatchPublisher.java` — метод `toProtoColumn`  
- `backend/monolith/src/.../service/TaskService.java` — lookup по columnId
- `backend/monolith/src/.../repository/TaskColumnRepository.java` — уже есть `findByTeamId`
- `backend/monolith/src/.../entity/TaskColumn.java` — `youGileColumnId` поле
