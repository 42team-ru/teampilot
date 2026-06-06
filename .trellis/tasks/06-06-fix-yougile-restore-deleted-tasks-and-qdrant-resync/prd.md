# fix: YouGile restore DELETED_FROM_YOUGILE tasks + Qdrant resync

## Goal

Задача с `localStatus=DELETED_FROM_YOUGILE` в текущей реализации никогда не восстанавливается,
если снова появляется в YouGile (напр., из-за лага сети). `updateTask` молча обновляет поля,
но не снимает `deleted=true` и не публикует restore-событие → Qdrant продолжает считать задачу удалённой.

## What I Already Know

- `reconcileDeletedTasks` помечает задачу `DELETED_FROM_YOUGILE` + `deleted=true`, если её нет в remoteTasks.
- `syncRemoteTask` находит задачу по `externalId` (без фильтрации по `localStatus`) → вызывает `updateTask`.
- `updateTask` НЕ проверяет `deleted` / `DELETED_FROM_YOUGILE` → задача остаётся помеченной удалённой.
- Если `changed=false` (поля не изменились) → вообще никакого события не отправляется.
- `publishCancelled` → Kafka `tasks.lifecycle` тип `CANCELLED` → llm-worker `delete_task(task_id)` в Qdrant.
- `publishImported` / `publishCreated` → тип `CONFIRMED` → llm-worker `store_task(...)` (upsert в Qdrant).
- `publishUpdated` → тип `UPDATED` → llm-worker `store_task(...)` тоже делает upsert.
- Qdrant-сторона уже правильно обрабатывает CONFIRMED/UPDATED через `store_task` (upsert). Проблема только в Java.

## Requirements

1. В `YouGileBoardSyncService.updateTask`: если задача имеет `deleted=true` или `localStatus=DELETED_FROM_YOUGILE`,
   восстановить её: `deleted=false`, `localStatus=ACTIVE`, `changed=true`.
2. При восстановлении вызывать `taskEventPublisher.publishImported(task)` — отправляет `CONFIRMED`,
   что вынудит llm-worker сделать upsert в Qdrant.
3. Событие публиковать до или вместо стандартных `publishUpdated` / `publishColumnChanged`,
   потому что `publishImported` уже полностью описывает ситуацию «задача вернулась».

## Acceptance Criteria

- [ ] Задача с `DELETED_FROM_YOUGILE` и `deleted=true`, вновь появившаяся в remoteTasks,
      получает `localStatus=ACTIVE`, `deleted=false` после `syncRemoteTask`.
- [ ] В Kafka `tasks.lifecycle` отправляется событие типа `CONFIRMED` для восстановленной задачи.
- [ ] Если содержимое задачи при этом изменилось (title/description/deadline/assignee),
      эти изменения тоже применяются за один save.
- [ ] Если содержимое не изменилось — всё равно save + CONFIRMED (idempotent upsert в Qdrant).

## Definition of Done

- Изменение в одном файле: `YouGileBoardSyncService.java`
- Нет новых зависимостей

## Technical Approach

В `updateTask` первым делом:

```java
boolean restored = false;
if (task.isDeleted() || task.getLocalStatus() == TaskLocalStatus.DELETED_FROM_YOUGILE) {
    task.setDeleted(false);
    task.setLocalStatus(TaskLocalStatus.ACTIVE);
    changed = true;
    restored = true;
}
```

В конце метода, если `changed`:
- Если `restored` → `taskEventPublisher.publishImported(task)` (→ CONFIRMED → Qdrant upsert)
- Если не `restored` — поведение прежнее: `publishUpdated` / `publishColumnChanged`

## Out of Scope

- Ретрай механизм для `reconcileDeletedTasks` (отдельная задача)
- Уведомление пользователя о восстановлении задачи в Telegram

## Technical Notes

- Файл: `backend/monolith/src/main/java/ru/team42/monolith/service/YouGileBoardSyncService.java`
- Метод: `updateTask` (строка 157)
- Qdrant-потребитель: `llm-worker/main.py:56` — `store_task` для CONFIRMED/UPDATED
