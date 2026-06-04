# add-telegram-login-to-register-and-patch-user

## Goal

Починить передачу `telegram_login` при регистрации и обеспечить дозапись логина для уже существующих пользователей при входе в бот.

## Requirements

### Шаг 1 — `/register`: передавать `telegram_login` из Telegram
- В `bot/handlers/registration.py` при вызове `register_user(...)` передавать `telegram_login=message.from_user.username` (сейчас захардкожен `None`)

### Шаг 2 — `PATCH /users/{id}`: поддержка `telegramLogin`
- Backend: добавить поле `telegramLogin` в `UpdateUserRequest`
- Backend: в `UserService.update` писать `telegramLogin` **только если** в БД он сейчас `null` (не перетирать)
- `/users/me` не трогать — изменение только для `/users/{id}`

### Шаг 3 — `update_user` в боте: передавать `telegram_login`
- В `bot/services/user_service.py`: добавить параметр `telegram_login` в `update_user`, включить в тело запроса
- В `bot/handlers/registration.py`: при вызове `update_user(...)` передавать `telegram_login=message.from_user.username`

### Шаг 4 — Проверка при входе: дозаписать или заблокировать
- При каждом входе пользователя в бот (в `NeedsRegistration` фильтре или новом middleware) проверять:
  - Если у пользователя в БД нет `telegramLogin` И `from_user.username` не пустой → тихо вызвать `PATCH /users/{id}` с `telegram_login` и продолжить
  - Если у пользователя в БД нет `telegramLogin` И `from_user.username` тоже `None` → заблокировать с сообщением «Для использования бота установите @username в настройках Telegram и повторите попытку»

## Acceptance Criteria

- [ ] `POST /auth/register` сохраняет `telegramLogin` если бот передал username
- [ ] `PATCH /users/{id}` принимает `telegramLogin`, записывает только если было null
- [ ] `/users/me` не изменяется
- [ ] Бот при регистрации нового пользователя передаёт `from_user.username`
- [ ] Бот при обновлении имени (update_user) передаёт `from_user.username`
- [ ] Бот при входе пользователя с пустым telegramLogin тихо патчит его через `/users/{id}` если username известен
- [ ] Бот блокирует пользователя без Telegram username с понятным сообщением

## Definition of Done

- Код компилируется (`gradlew :monolith:bootJar -x test`)
- Бот запускается без ошибок импорта
- Все изменённые файлы консистентны между собой

## Out of Scope

- Изменение `/users/me`
- Периодическая фоновая синхронизация username
- UI/фронтенд

## Technical Notes

**Файлы изменений:**
- `backend/monolith/src/main/java/ru/team42/monolith/dto/request/UpdateUserRequest.java` — добавить `String telegramLogin`
- `backend/monolith/src/main/java/ru/team42/monolith/service/UserService.java` — условная запись telegramLogin
- `bot/handlers/registration.py` — передавать `from_user.username` в register_user и update_user
- `bot/services/user_service.py` — добавить `telegram_login` параметр в update_user
- `bot/handlers/registration.py` или новый middleware — логика проверки при входе

**Ограничения:**
- Не писать Flyway-миграции, ddl-auto: update справится
- Исключения только через `AppException`
- Ответы контроллеров через `ResponseUtils`
