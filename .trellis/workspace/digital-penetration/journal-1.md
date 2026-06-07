# Journal - digital-penetration (Part 1)

> AI development session journal
> Started: 2026-06-03

---



## Session 1: Kafka task state events, Qdrant sync, LLM Worker cleanup

**Date**: 2026-06-06
**Task**: Kafka task state events, Qdrant sync, LLM Worker cleanup
**Branch**: `master`

### Summary

Добавили два Kafka-топика: tasks.state (бот-уведомления: CREATED/COLUMN_CHANGED/CANCELLED) и tasks.lifecycle (Qdrant sync: CONFIRMED/UPDATED/CANCELLED). Покрыли все 8 точек мутации задачи. Исправили баг с epoch millis в YouGile. Починили Jackson: JavaTimeModule вместо lenientInstantModule, lenient String deserializer для YouGile API. LLM Worker: убрали fallback-код, priority, восстановили минимальный qdrant.py. Обнаружили и исправили критический баг: Spring сериализует camelCase, Python модели должны использовать Field(alias=...).

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `24b4fcd` | (see git log) |
| `8145d63` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: Evening sync excuse feature

**Date**: 2026-06-07
**Task**: Evening sync excuse feature
**Branch**: `master`

### Summary

Added /excuse command: user writes /excuse [reason] in private chat, bot shows inline keyboard to pick team (or all teams), excused users are filtered from evening sync at 18:00, manager summary includes excused list with reasons. Fixed Cyrillic callback_data byte overflow and double-counting bug in summary.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `3ea2bb3` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: SyncStateService + ExcuseService → PostgreSQL

**Date**: 2026-06-07
**Task**: SyncStateService + ExcuseService → PostgreSQL
**Branch**: `master`

### Summary

Replaced in-memory ConcurrentHashMap session state with JPA/PostgreSQL: new entities SyncSession, SyncUserState, SyncExcuse + repositories. Drop-in replacement — public API unchanged. Fixed entity→service layer violation (UserSyncStatus extracted to entity.enums). ddl-auto handles schema, no Flyway migrations.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `bce3bec` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: Fix: YouGile недоступен → задачи больше не отменяются

**Date**: 2026-06-07
**Task**: Fix: YouGile недоступен → задачи больше не отменяются
**Branch**: `master`

### Summary

При недоступности YouGile fetchAllTasksForBoard и fetchColumns теперь бросают исключение вместо возврата пустого списка. Планировщик уже ловит его — reconcileDeletedTasks не вызывается, задачи и колонки не помечаются удалёнными ложно.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `de1e2c0` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
