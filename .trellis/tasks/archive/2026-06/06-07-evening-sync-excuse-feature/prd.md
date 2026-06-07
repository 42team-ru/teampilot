# Evening Sync — Excuse Feature

## Goal

Пользователь может написать `/excuse [причина]` в личку боту в любое время (до или во время синка) и быть исключённым из вечернего синка на сегодня. В саммари менеджеру отображается имя + причина.

## Requirements

* Команда `/excuse [причина]` в личке боту запускает flow:
  1. Бот запрашивает список команд пользователя через `GET /excuse/teams?telegramUserId=xxx`
  2. Если одна команда — сразу подтверждает, без клавиатуры
  3. Если несколько — показывает `InlineKeyboardMarkup` с кнопками команд + «Все команды»
  4. После выбора бот вызывает `POST /excuse {telegramUserId, teamId, reason}` и отвечает «Понял, тебя не жду на синке сегодня»
* Если причина не указана (`/excuse` без текста) — сохраняется «без объяснений»
* В 18:00 при старте синка excused-пользователи фильтруются из `memberIds` и не получают промпт
* Если синк уже идёт (18:00–19:00) и пользователь пишет `/excuse`:
  * Статус в `SyncStateService` меняется на `EXCUSED`
  * Бот больше не ждёт ответа от этого пользователя
  * Промпт не редактируется и не удаляется
* В итоговом саммари менеджеру — отдельный блок: «Не участвовали: Иван — болею, Петя — без объяснений»
* Хранение — in-memory (сбрасывается при `closeSession` или при рестарте)

## Acceptance Criteria

* [ ] `/excuse болею` в личке → бот показывает клавиатуру с командами (или сразу подтверждает если одна)
* [ ] После выбора команды → пользователь не получает синк-промпт в 18:00
* [ ] `/excuse` во время синка → пользователь помечается EXCUSED, больше не ждут ответа
* [ ] В саммари менеджера виден список excused с причинами
* [ ] `/excuse` без текста → причина «без объяснений»
* [ ] «Все команды» → excuse применяется ко всем командам пользователя

## Definition of Done

* Все AC выполнены
* Протестировано через `/test_sync` + ручной тест `/excuse`

## Technical Approach

**Backend — 4 изменения:**
1. Новый `ExcuseService` (`@Service`) — `Map<Long, Map<UUID, String>>` телеграм→{команда→причина}; методы `excuse(telegramId, teamId, reason)`, `isExcused(telegramId, teamId)`, `getExcused(teamId)`, `clearTeam(teamId)`
2. `SyncController` — `GET /excuse/teams?telegramUserId` + `POST /excuse {telegramUserId, teamId, reason}`
3. `EveningSyncService.startSyncForTeam()` — до формирования `memberIds` фильтровать через `excuseService.isExcused()`
4. `SyncStateService` — добавить `EXCUSED` в `UserSyncStatus`; `EveningSyncService.sendSummaryForTeam()` — добавить блок excused в сообщение менеджеру; `closeSyncAndSendSummary` вызывает `excuseService.clearTeam()`

**Bot — 3 изменения:**
1. `bot/handlers/sync.py` — handler `cmd_excuse`: парсит причину, вызывает `GET /excuse/teams`, строит клавиатуру (или сразу `POST /excuse` если одна команда)
2. `bot/keyboards/sync.py` — `build_excuse_keyboard(teams, reason)` с кнопками `excuse_team:<team_id>:<reason>` и `excuse_all:<reason>`
3. `bot/handlers/sync.py` — callback-хендлеры `excuse_team:` и `excuse_all:` → вызов `POST /excuse`

## Decision (ADR-lite)

**Context**: Нужно хранить отмазки между моментом подачи (до 18:00) и стартом синка.
**Decision**: In-memory `ExcuseService` (как `TaskProposalCache`).
**Consequences**: При рестарте сервиса до 18:00 отмазки теряются. Приемлемо для хакатона.

## Out of Scope

* Многодневные отмазки
* Хранение в БД / persistence
* Удаление/редактирование уже отправленного синк-промпта

## Technical Notes

* `SyncStateService.UserSyncStatus` — добавить `EXCUSED`
* `TaskProposalCache` — образец для `ExcuseService`
* `TeamUserRepository.findAllByUserTelegramId()` — уже есть, используем для получения команд пользователя
* Синк: 18:00 старт, 19:00 саммари (`EveningSyncScheduler`)
* Существующий admin-тест: `/test_sync`, `/test_sync_summary`
