# notifications: deadline reminder, stale alert

## Goal

Добавить два типа уведомлений пользователям через Telegram-бота:
1. **Дедлайн-напоминание** — «Задача X через 2 часа» (личное сообщение исполнителю, однократно)
2. **Устаревший статус** — «Вы не обновили статус задачи X» (исполнитель не двигает задачу 24+ ч)

Spring-монолит публикует события в топик `bots.notifications`, Telegram-бот читает и доставляет.

## Requirements

* Scheduler каждые ~5 минут ищет задачи `ACTIVE` с `deadline` в окне `[now+1h55m, now+2h05m]` и `deadline_notified_at IS NULL`
* При совпадении проставляет `deadlineNotifiedAt = now`, публикует `BotNotificationEvent` (type=DEADLINE) в `bots.notifications`
* Scheduler раз в час ищет задачи `ACTIVE` с `assignee != null`, где последняя запись `task_status_history.created_at < now - 24h` (или записей нет совсем)
* При совпадении публикует `BotNotificationEvent` (type=STALE) в `bots.notifications`
* `BotNotificationEvent` содержит: `telegramId` (assignee), `chatId` (team), `type`, `taskId`, `taskTitle`
* Если у задачи нет assignee — уведомление не отправляется
* Получатель stale-алерта — только assignee (не менеджер)

## Acceptance Criteria

* [ ] Assignee получает личное сообщение «Задача "X" — до дедлайна 2 часа»
* [ ] Повторное уведомление о дедлайне не уходит (поле `deadlineNotifiedAt` проставлено)
* [ ] Если дедлайн обновился — поле сбрасывается, новое уведомление уйдёт снова
* [ ] Assignee получает «Вы давно не обновляли статус задачи "X"» если 24ч без движения
* [ ] Задача без assignee — уведомление не отправляется

## Definition of Done

* Unit-тесты для `NotificationScheduler` (без Kafka, мок publisher)
* Lint / CI зелёный
* Только `AppException`, без `RuntimeException` напрямую

## Out of Scope

* Вечерний дайджест — отложен
* Push в YouGile по нотификациям
* Snooze / повторные напоминания
* Уведомления менеджеру команды

## Decision Log

| Решение | Выбор | Причина |
|---|---|---|
| Идемпотентность deadline | `deadlineNotifiedAt` в `Task` | Проще, без лишних таблиц |
| Порог stale | 24 часа | Стандарт daily standup |
| Получатели stale | только assignee | Личная ответственность |
| Вечерний дайджест | out of scope MVP | Отложено |

## Technical Notes

* **Паттерн планировщика**: `YouGileSyncScheduler` → `@Scheduled` (уже есть в `scheduler/`)
* **Паттерн публикации**: `TaskEventPublisher extends AbstractEventPublisher` → новый `NotificationEventPublisher`
* **Новое поле**: `Task.deadlineNotifiedAt: Instant` (nullable), `ddl-auto: update` применит автоматически
* **Deadline query**: `findByLocalStatusAndDeadlineBetweenAndDeadlineNotifiedAtIsNull(ACTIVE, from, to)` — Spring Data
* **Stale query**: `@Query` JPQL — задачи ACTIVE с assignee, где нет истории за 24ч:
  ```sql
  WHERE t.localStatus = ACTIVE AND t.assignee IS NOT NULL
    AND (NOT EXISTS (SELECT h FROM TaskStatusHistory h WHERE h.task = t AND h.createdAt > :threshold))
  ```
* **Ключевые файлы**:
  - `entity/Task.java` — добавить `deadlineNotifiedAt`
  - `repository/TaskRepository.java` — два новых метода
  - `scheduler/NotificationScheduler.java` — новый класс
  - `service/NotificationEventPublisher.java` — новый класс
  - `event/BotNotificationEvent.java` — новый record
