# filter-tasks-by-kanban-column

## Goal

Заменить хардкоженную фильтрацию задач по `localStatus` (ACTIVE / PENDING_APPROVAL / DELETED_FROM_YOUGILE)
на динамическую фильтрацию по **колонкам канбан-доски** команды.
Колонки приходят из YouGile, хранятся в `TaskColumn` на беке.

## What I already know

* Бек: `TaskColumn` entity — поля `id`, `team`, `title`, `youGileColumnId`
* Бек: `TaskColumnRepository.findByTeamId(UUID)` — уже есть, но без REST-эндпоинта
* Бек: `GET /tasks` принимает `chatId`, `assignee`, `localStatus` — `columnId` не поддерживает
* Бек: `TaskResponse.column` уже содержит `{columnId, youGileColumnId, title}` в каждой задаче
* Бот: фильтрация через `_local_status_param()` в `task_service.py` → `localStatus` параметр
* Бот: кнопки фильтров сейчас хардкодом в клавиатурах (Новые задачи / Мои задачи / Задачи команды / Доска)
* Места вызова: `team_context_manager_tasks_keyboard` и `team_context_member_tasks_keyboard`

## Open Questions

*(закрыты)*

## Requirements

### Backend

* `GET /tasks/columns?chatId=...` — вернуть `[{id, title}]` колонок команды (авторизация: `X-Bot-Secret`)
* `GET /tasks?columnId=<uuid>` — фильтровать задачи по колонке (добавить параметр к существующему эндпоинту)

### Bot

* `get_team_columns(chat_id, telegram_id)` в `bot/services/task_service.py`
* Панель "Задачи" (менеджер и участник): `📥 Мои задачи` наверху, затем динамические кнопки колонок
* Кнопка `🆕 Новые задачи` (PENDING_APPROVAL) — убрать
* При нажатии на колонку → показать задачи только этой колонки
* Если колонок нет → сообщение "Канбан-доска не настроена" + `← К команде`, кнопка `📥 Мои задачи` остаётся

## Acceptance Criteria (evolving)

* [ ] `GET /tasks/columns?chatId=123` возвращает список `[{id, title}]`
* [ ] `GET /tasks?columnId=...` фильтрует задачи по колонке
* [ ] В боте при входе в "Задачи" команды показываются кнопки с названиями колонок
* [ ] Нажатие на колонку показывает задачи только этой колонки
* [ ] Если колонок нет — понятное сообщение

## Definition of Done

* Бек: эндпоинты работают, интегрируются с существующей auth (X-Telegram-Id / X-Bot-Secret)
* Бот: нет хардкоженных статусов в задачном флоу
* Lint / typecheck чистые

## Out of Scope

* Создание/редактирование колонок из бота
* Синхронизация колонок (это уже делается через YouGile)
* Пагинация колонок (колонок обычно < 10)

## Technical Notes

* Backend файлы: `TaskController.java`, `TaskService.java`, `TaskRepository.java`, `TaskColumnRepository.java`
* Bot файлы: `bot/services/task_service.py`, `bot/keyboards/member.py`, `bot/handlers/member.py`
* Авторизация бека: `X-Bot-Secret` для бот-запросов
