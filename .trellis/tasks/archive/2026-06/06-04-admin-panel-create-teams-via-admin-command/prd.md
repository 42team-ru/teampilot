# Admin panel: create teams via /admin command

## Goal

Добавить команду `/admin` (только в личке), доступную пользователям с ролью `SYSTEM_ADMIN`.
Панель включает создание команды через `POST /admin/teams`.

## What I already know

- `handlers/admin.py` — уже есть `show_admin_panel()`, вызывается из `/start` если `systemRole == "SYSTEM_ADMIN"`
- `/admin` команды **нет** — нужно создать
- Swagger: `POST /admin/teams` принимает `{telegramChatId?, chatTitle, kanbanId?, kanbanApiKey?, adminTelegramId, adminUsername}`
- `adminTelegramId` и `adminUsername` берутся из `message.from_user` — спрашивать не нужно
- `services/admin_service.py` — нужно добавить `create_team()` → `POST /admin/teams`
- Роль SYSTEM_ADMIN проверяется через `GET /users/{telegramId}` в `admin_service.py`
- Текущие кнопки панели: 🔗 Ссылка для вступления | 💬 Добавить бота в чат | 👥 Участники команды
- Новая кнопка: 🏢 Создать команду → FSM-флоу

## Open Questions

- (resolved) Канбан поля при создании команды: обязательные или опциональные?

## Requirements

- `/admin` в личке: проверить роль → показать `admin_main_keyboard`
- `/admin` в группе: игнорировать / отказать
- Только `SYSTEM_ADMIN` видит панель; остальным — «нет доступа»
- Кнопка «🏢 Создать команду» → FSM: chatTitle (обязательно) → kanbanId (кнопка «Пропустить») → kanbanApiKey (кнопка «Пропустить») → `POST /admin/teams`
- После создания — подтверждение с teamId

## Acceptance Criteria

- [ ] `/admin` в личке для SYSTEM_ADMIN → открывает панель
- [ ] `/admin` в личке для не-SYSTEM_ADMIN → «нет доступа»
- [ ] `/admin` в группе → игнорируется
- [ ] FSM «Создать команду»: chatTitle обязателен; на kanbanId и kanbanApiKey появляется кнопка «Пропустить»
- [ ] После `POST /admin/teams` бот отвечает с названием и teamId
- [ ] В любой момент `/cancel` — сбросить FSM

## Out of Scope

- Список команд (GET /teams/my) — отдельная задача
- Редактирование/удаление команды через панель
- Назначение менеджеров

## Technical Notes

- `POST /admin/teams` → `services/admin_service.py::create_team()`
- FSM: `CreateTeamStates` → `states/admin.py` (новый файл)
- Кнопка добавляется в `keyboards/admin.py::admin_main_keyboard()`
- `/admin` handler → `handlers/admin.py` (новый `@router.message(Command("admin"))`)
- `/cancel` в FSM состояниях CreateTeam — через общий `cmd_cancel` в `setup.py` (только `private`) — уже покрыт
