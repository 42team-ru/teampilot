# Add X-Telegram-Id header to all bot API requests

## Goal

Добавить заголовок `X-Telegram-Id: {telegram_id}` ко всем HTTP-запросам бота к бэкенду,
чтобы бэкенд мог идентифицировать пользователя, от имени которого действует бот.

## Requirements

- Каждая функция в `team_service.py`, `admin_service.py`, `task_service.py` принимает `telegram_id: int | None = None`
- Если `telegram_id` передан — добавляем `X-Telegram-Id` к заголовкам запроса
- Все вызывающие хэндлеры передают `message.from_user.id` / `callback.from_user.id`
- Bot-level операции без пользовательского контекста (deactivate_team, bot_added) — передают `None`

## Acceptance Criteria

- [ ] Все функции в 3 сервисных файлах имеют параметр `telegram_id`
- [ ] Заголовок добавляется когда telegram_id не None
- [ ] Все хэндлеры обновлены и передают telegram_id

## Out of Scope

- Изменение бэкенда
- Добавление авторизации через JWT

## Technical Notes

Затронутые файлы:
- bot/services/team_service.py
- bot/services/admin_service.py
- bot/services/task_service.py
- bot/handlers/auth.py
- bot/handlers/setup.py
- bot/handlers/admin.py
- bot/handlers/tasks_commands.py
