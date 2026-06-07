# fix: YouGile недоступен → задачи не должны отменяться

## Goal

При недоступности YouGile API синхронизатор ошибочно отменяет все активные задачи.
Нужно защитить `reconcileDeletedTasks` (и аналогичную логику в `syncColumns`) от ложных удалений.

## Что уже известно (из кода)

* `YouGileService.fetchAllTasksForBoard` (`kanban/YouGileService.java:133-146`):
  при любом исключении (коннект, таймаут, 5xx) логирует ошибку и возвращает `List.of()`.
* `YouGileBoardSyncService.syncTeam` (`service/YouGileBoardSyncService.java:49-70`):
  берёт результат `fetchAllTasksForBoard`, строит `remoteIds` → вызывает `reconcileDeletedTasks`.
* `reconcileDeletedTasks` (`line 73-87`): все задачи, которых нет в `remoteIds`, получают
  `DELETED_FROM_YOUGILE` + `publishCancelled` → бот показывает "❌ Отменено задач: N".
* **Та же проблема** в `syncColumns` (`line 90-122`): если `fetchColumns` упадёт и вернёт пустой список,
  все локальные колонки помечаются `deleted=true`.

## Подходы

**Подход A: `fetchAllTasksForBoard` бросает исключение — `syncTeam` перехватывает и выходит** (рекомендуется)

* `fetchAllTasksForBoard` re-throw исключение вместо `return List.of()`.
* `syncTeam` оборачивает вызов в try-catch: при исключении — `log.warn` + `return` (без reconcile).
* Аналогично для `syncColumns` и `syncStickers`.
* Плюсы: минимальное изменение, идиоматично, reconcile не запускается при ошибке.
* Минусы: нужно убедиться, что другие вызывающие `fetchAllTasksForBoard` тоже готовы к исключению.

**Подход B: `Optional<List<...>>` как возврат**

* Меняем сигнатуру на `Optional<List<YouGileTaskResponse>>`: `empty` = ошибка, `of(List.of())` = успех.
* `syncTeam` проверяет `isPresent()`.
* Минусы: ломает существующие вызовы (`listFromYouGile` в `TaskService`), больше изменений.

## Requirements

* При недоступности YouGile (таймаут / 5xx / исключение) `reconcileDeletedTasks` **не вызывается**.
* При недоступности YouGile `syncColumns` **не помечает** локальные колонки удалёнными.
* При недоступности YouGile `syncStickers` **не падает** с ошибкой (уже safe, но проверить).
* Поведение при реально пустой доске в YouGile не меняется.

## Acceptance Criteria

* [ ] Если `fetchAllTasksForBoard` бросает исключение → задачи **не** переходят в `DELETED_FROM_YOUGILE`
* [ ] Если `fetchColumns` бросает исключение → колонки **не** помечаются `deleted=true`
* [ ] Лог-сообщение на уровне `warn/error` при недоступности YouGile присутствует
* [ ] Задачи, действительно удалённые из YouGile (при успешном ответе), по-прежнему reconcile-ятся

## Definition of Done

* Изменения в `YouGileService` и `YouGileBoardSyncService`
* Нет регрессий в `YouGileSyncScheduler`

## Out of Scope

* Retry-механизм для YouGile API
* Алерты / метрики недоступности YouGile

## Technical Notes

* Файлы: `kanban/YouGileService.java`, `service/YouGileBoardSyncService.java`
* Другой вызывающий `fetchAllTasksForBoard`: `TaskService.listFromYouGile` (строка 382) —
  там исключение уместно (запрос пользователя), менять не нужно.
* `fetchColumns` вызывается только из `syncColumns` — безопасно менять сигнатуру.
