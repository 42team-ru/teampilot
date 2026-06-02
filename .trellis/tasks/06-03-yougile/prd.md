# PRD: Флоу добавления бота в группу и настройка YouGile борда

## Цель
Реализовать полный onboarding-флоу: от момента добавления бота в Telegram-группу до привязки YouGile борда и готовности к работе.

## Контекст
Бот находится в `bot/`. Использует aiogram 3.x, httpx, HTML parse_mode (по умолчанию), MemoryStorage для FSM.

## Что нужно создать / изменить

### Новые файлы
- `bot/states/__init__.py` — реэкспорт
- `bot/states/setup.py` — FSM: `GroupSetupStates` (waiting_for_token, waiting_for_board_select)
- `bot/services/__init__.py`
- `bot/services/yougile.py` — `YouGileClient` через httpx: validate_token(), get_projects()
- `bot/services/group_service.py` — register_group(), get_group(), is_group_configured(), deactivate_group()
- `bot/handlers/setup.py` — все хэндлеры флоу настройки

### Изменить
- `bot/keyboards/task.py` — добавить `build_projects_keyboard(projects)`
- `bot/main.py` — зарегистрировать `setup_router` ПЕРВЫМ
- `bot/storage.py` — добавить хранилище групп (Group dataclass + функции)

## Ключевые хэндлеры
1. `bot_added_to_group` — my_chat_member IS_NOT_MEMBER >> IS_MEMBER → DM или fallback-кнопка
2. `start_with_setup_deep_link` — `/start setup_{chat_id}` через кастомный фильтр
3. `process_yougile_token` — FSM waiting_for_token → валидация → список проектов
4. `process_board_selection` — FSM waiting_for_board_select → register_group → подтверждение
5. `bot_removed_from_group` — IS_MEMBER >> IS_NOT_MEMBER → deactivate_group
6. `cmd_setup_in_group` — команда /setup в группе (только для админов)

## Edge cases
- Группа уже настроена → переподключение
- TelegramForbiddenError → fallback deep link кнопка в группе
- callback_data лимит 64 байта → title хранить в FSM, в callback только board_id
- Токен уже настроен → спросить «перенастроить?»
- YouGile API timeout → сообщение «попробуй позже»
