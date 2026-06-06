# dedup-task-creation-same-title

## Goal

Когда в чат отправляются одинаковые (или похожие по содержанию) сообщения повторно — система не должна создавать дубликаты задач. Сейчас нет ни одного слоя проверки на дублирование: `TaskService.createFromLlmEvent()` создаёт задачу безусловно.

## What I already know

* `TaskService.createFromLlmEvent()` — единственная точка входа при создании LLM-задачи; нет никакой проверки на существование похожей задачи
* `Task` имеет поля: `title`, `team`, `localStatus` (PENDING_APPROVAL / ACTIVE / DELETED_FROM_YOUGILE), `deleted`
* `TaskRepository` — нет метода поиска по title; надо добавить
* LLM worker (`processor.py`) — `_extract_tasks()` не делает Qdrant lookup (в отличие от `_extract_statuses()`, который ищет по Qdrant)
* Дублирование происходит потому что повторные сообщения в Telegram → новые `ChatMessage` записи → новый батч → LLM извлекает те же задачи → Spring создаёт снова

## Assumptions

* Задача с тем же title (case-insensitive) для той же команды в статусе PENDING_APPROVAL или ACTIVE — дубликат
* Если предыдущая задача была отменена (DELETED_FROM_YOUGILE) — допустимо создать заново
* Приоритет MVP: защита на стороне Spring (надёжнее, не зависит от Qdrant/LLM)

## Open Questions

* (resolved ниже после выбора подхода)

## Requirements

* При попытке создать задачу с title, который уже есть у активной задачи этой команды — пропустить создание, залогировать WARN
* Проверка case-insensitive
* Логика не ломает ручное создание задач (TaskController) — там свои эндпоинты

## Acceptance Criteria

* [ ] Отправить одинаковые сообщения в чат дважды → задачи создаются только один раз
* [ ] Лог содержит WARN с title и teamId при пропуске дубликата
* [ ] Если задача была отменена → повторная отправка тех же сообщений → задача создаётся заново
* [ ] Существующие тесты не ломаются

## Definition of Done

* Код изменён в Spring (TaskRepository + TaskService)
* Юнит-тест на дедупликацию добавлен (если есть тестовое покрытие в проекте)
* Lint/build проходит

## Technical Approach (выбранный)

**Слой 1: LLM worker** — `processor.py` `_extract_tasks()`:
```python
from infra.qdrant import is_task_duplicate
# перед append:
if is_task_duplicate(extraction.title, extraction.description or "", batch.team_id):
    logger.info(f"Skipping duplicate task {extraction.title!r} (Qdrant match)")
    continue
```
`is_task_duplicate()` уже реализована в `qdrant.py` с `DEDUP_THRESHOLD = 0.92`.

**Слой 2: Spring fallback** — `TaskRepository.java`:
```java
boolean existsByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
    UUID teamId, String title, Collection<TaskLocalStatus> statuses);
```
В `TaskService.createFromLlmEvent()` перед созданием:
```java
boolean duplicate = taskRepository.existsByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
    team.getId(), event.getTitle(),
    List.of(TaskLocalStatus.PENDING_APPROVAL, TaskLocalStatus.ACTIVE));
if (duplicate) {
    log.warn("Skipping duplicate task title='{}' teamId={}", event.getTitle(), event.getTeamId());
    return taskRepository
        .findFirstByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
            team.getId(), event.getTitle(),
            List.of(TaskLocalStatus.PENDING_APPROVAL, TaskLocalStatus.ACTIVE))
        .orElseThrow();
}
```

## Decision (ADR-lite)

**Context**: Без дедупликации повторная отправка тех же сообщений создаёт дублирующие задачи.  
**Decision**: Вариант C — два слоя: LLM worker (Qdrant) + Spring fallback (title-match в БД).  
**Consequences**:
- Qdrant актуален через `run_lifecycle_consumer` (CONFIRMED → store, CANCELLED → delete)
- `is_task_duplicate()` уже реализована в `qdrant.py`, просто не вызывается в `_extract_tasks()`
- Spring-слой защищает если Qdrant недоступен (`is_task_duplicate` возвращает False при ошибке)

## Out of Scope

* Семантическая дедупликация по содержанию (похожие, но по-другому сформулированные задачи)
* Дедупликация задач, созданных вручную через REST API
* Изменение ChatMessageBatchingService

## Technical Notes

* Файлы: `TaskRepository.java`, `TaskService.java`
* `TaskLocalStatus`: PENDING_APPROVAL, ACTIVE, DELETED_FROM_YOUGILE
* `Task.deleted` — soft-delete флаг (отдельно от localStatus)
