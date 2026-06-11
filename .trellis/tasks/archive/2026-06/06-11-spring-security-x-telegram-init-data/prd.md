# Spring Security — X-Telegram-Init-Data верификация (Mini App)

## Goal

Реализовать аутентификацию Telegram Mini App на бэкенде:
1. `TelegramInitDataVerifier` — верифицирует HMAC-SHA256 строки `initData` (алгоритм Mini App, отличается от OAuth-виджета)
2. `POST /auth/telegram/mini-app` — эндпоинт логина для Mini App, читает заголовок `X-Telegram-Init-Data`, верифицирует, возвращает JWT + `AuthResponse`
3. Обновить `TelegramAuthFilter` — добавить попытку `X-Telegram-Init-Data` как третий метод аутентификации (после JWT, до `X-Telegram-Id`)

## What I already know

- `TelegramAuthFilter` уже обрабатывает: JWT Bearer → `X-Telegram-Id` (сырой, без верификации) → `X-Bot-Secret`
- `TelegramOAuthVerifier` существует для OAuth-виджета — ключ `SHA-256(botToken)`, **не** для Mini App
- Mini App `api/client.ts` шлёт `X-Telegram-Init-Data` на **каждый** запрос через interceptor
- Mini App `auth.ts` уже содержит `loginWithInitData()` → `POST /auth/telegram/mini-app` (эндпоинт не существует)
- `AppProperties.telegram.botToken` уже есть
- `AuthResponse` — существующий DTO: `{ token, userId, ... }`

## Алгоритм верификации initData (Mini App — отличается от OAuth)

```
initData = "auth_date=1686...&hash=abc...&user=%7B%22id%22%3A123%7D..."

1. URL-decode строку, разбить по "&" на key=value пары
2. Вытащить hash, убрать из остальных
3. Оставшиеся пары → отсортировать по ключу → соединить "\n"
4. secretKey = HMAC-SHA256(data=botToken, key="WebAppData")   ← НЕ sha256(botToken)!
5. signature  = HMAC-SHA256(data=data_check_string, key=secretKey)
6. HEX(signature) == hash → valid
```

## Requirements

- `TelegramInitDataVerifier` (новый `@Component`)
  - `verify(String initData): boolean` — проверяет HMAC
  - `extractTelegramId(String initData): long` — парсит `user.id` из JSON поля `user`
  - `extractUserInfo(String initData): TelegramUserInfo` — парсит first_name, username, photo_url
- `POST /auth/telegram/mini-app` (в `AuthController`)
  - Читает заголовок `X-Telegram-Init-Data`
  - Отдаёт `401` если заголовок отсутствует или HMAC невалиден
  - Находит или создаёт User по `telegram_id`
  - Возвращает `AuthResponse` (JWT + userId + ...) с `200 OK`
- `TelegramAuthFilter` — добавить `tryAuthenticateWithInitData()` между JWT и `X-Telegram-Id`

## Acceptance Criteria

- [ ] `POST /auth/telegram/mini-app` с валидным `X-Telegram-Init-Data` → `200` + JWT
- [ ] `POST /auth/telegram/mini-app` без заголовка → `401`
- [ ] `POST /auth/telegram/mini-app` с невалидным HMAC → `401`
- [ ] Последующий запрос с JWT Bearer работает (уже работает через `TelegramAuthFilter`)
- [ ] Запрос с валидным `X-Telegram-Init-Data` без JWT → аутентифицируется напрямую через фильтр

## Open Questions

- **Q1**: Когда пользователь не найден по `telegram_id` (первый вход через Mini App без бота):
  - **A (рекомендую)**: авто-создать пользователя из данных initData (`telegram_id`, `first_name`, `username`) → бесшовный онбординг
  - **B**: вернуть `401` с описанием "Please start the bot first" → пользователь обязан сначала запустить бота

## Technical Approach

**Файлы для создания/изменения:**
- `security/TelegramInitDataVerifier.java` — NEW
- `security/TelegramAuthFilter.java` — добавить tryAuthenticateWithInitData()
- `rest/AuthController.java` — добавить POST /auth/telegram/mini-app
- `service/AuthService.java` — добавить loginWithMiniApp(HttpServletRequest)

## Decision (ADR-lite)

**Context**: Mini App отправляет `initData` (HMAC-подписанную строку Telegram) и ждёт JWT в ответ.
**Decision**: Авто-создать пользователя из initData при первом входе (telegram_id, first_name, username).
**Consequences**: пользователь не привязан к команде → видит экран онбординга → создаёт или вступает в команду.

## Out of Scope

- Верификация `auth_date` (expiry check) — пропускаем для MVP хакатона
- Тесты

## Technical Notes

- Алгоритм: [Telegram Docs — Mini Apps initData](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)
- `TelegramOAuthVerifier` — НЕ переиспользовать, алгоритм ключа разный
- Jackson ObjectMapper для парсинга JSON поля `user` из initData
