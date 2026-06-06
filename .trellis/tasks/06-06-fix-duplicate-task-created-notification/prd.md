# fix-duplicate-task-created-notification

## Goal

При создании задачи бот отправляет два отдельных сообщения в чат (2N при N задачах). Нужно сделать одно.

## Root Cause

В `TaskService.java` при каждом подтверждении задачи (авто и ручное) вызываются оба метода:

```java
taskEventPublisher.publishConfirmation(saved, true);  // → BOTS_TASKS
taskEventPublisher.publishCreated(saved);             // → TASKS_STATE (CREATED) + TASKS_LIFECYCLE
```

Бот подписан на оба топика и батчит каждый независимо → 2 сообщения.

## Approach (выбранный)

**Добавить `columnTitle` в `TaskConfirmationEvent`** (Java) и **заглушить `TASKS_STATE` CREATED в боте**.

- `TaskConfirmationEvent` получает поле `columnTitle`
- `publishConfirmation` передаёт `task.getColumn().getTitle()` (если есть)
- Бот в `_send_task_confirmation` / `_flush_confirmations` показывает колонку
- В `_dispatch` бота `TASKS_STATE` CREATED → просто `return` (не отображать)
- `TASKS_STATE` CREATED всё ещё публикуется в Kafka (для потенциальных будущих консьюмеров), бот просто его игнорирует
- `TASKS_LIFECYCLE` не трогаем

## Requirements

* Одно батч-сообщение вместо двух при создании задач
* Одиночное сообщение (N=1): название, колонку, исполнителя, дедлайн — как сейчас
* Батч-сообщение (N>1): только название, исполнитель, дедлайн — без колонки (и так много инфо)
* При N=1 формат сообщения не деградирует
* `TASKS_STATE` COLUMN_CHANGED и CANCELLED продолжают работать как прежде

## Acceptance Criteria

* [ ] При создании 3 задач подряд в чат приходит ровно 1 сообщение
* [ ] Сообщение содержит колонку (📂) для каждой задачи
* [ ] Смена колонки (`COLUMN_CHANGED`) по-прежнему уведомляет
* [ ] Отмена задачи (`CANCELLED`) по-прежнему уведомляет

## Files in Scope

- `backend/monolith/src/main/java/ru/team42/monolith/event/TaskConfirmationEvent.java`
- `backend/monolith/src/main/java/ru/team42/monolith/service/TaskEventPublisher.java`
- `bot/kafka/consumer.py`

## Out of Scope

* Изменение формата `TASKS_STATE` CREATED топика
* Удаление вызова `publishCreated` из Java (lifecycle событие нужно оставить)
* Изменение логики батчинга (3-секундное окно остаётся)
