# Telegram OAuth For Extension Research

## Sources

* `backend/monolith/src/main/java/ru/team42/monolith/rest/AuthController.java`
* `backend/monolith/src/main/java/ru/team42/monolith/dto/request/TelegramOAuthRequest.java`
* `backend/monolith/src/main/java/ru/team42/monolith/dto/response/TelegramAuthResponse.java`
* `backend/monolith/src/main/java/ru/team42/monolith/service/AuthService.java`
* `backend/monolith/src/main/java/ru/team42/monolith/security/TelegramOAuthVerifier.java`
* Official Telegram Login docs: `https://core.telegram.org/widgets/login-legacy`
* Official Chrome identity docs: `https://developer.chrome.com/docs/extensions/reference/api/identity`

## Backend Contract

Backend exposes:

* `POST /auth/telegram`

Request:

```json
{
  "id": 123456789,
  "first_name": "Ivan",
  "last_name": "Petrov",
  "username": "ivan",
  "photo_url": "https://...",
  "auth_date": 1710000000,
  "hash": "..."
}
```

Response:

```json
{
  "userId": "uuid",
  "telegramId": 123456789,
  "systemRole": "USER",
  "token": "jwt"
}
```

Backend verifies:

* signature: HMAC-SHA-256 over Telegram data-check-string using SHA-256(bot token);
* freshness: `auth_date` must be no older than 24h;
* user upsert by Telegram ID;
* JWT includes `telegramId` and `role` claims.

## Extension Approach

Do not load Telegram's remote widget script inside extension pages. MV3 extension pages should not rely on remotely hosted executable script.

Recommended flow:

1. Add `identity` permission.
2. Use `chrome.identity.getRedirectURL('telegram-auth')`.
3. Open Telegram legacy auth directly with `chrome.identity.launchWebAuthFlow`:
   * URL: `https://oauth.telegram.org/auth`
   * params: `bot_id`, `origin`, `return_to`, optional `request_access`, `lang`
4. Telegram redirects back to the chromiumapp redirect URL with `tgAuthResult` in hash.
5. Parse and base64url-decode `tgAuthResult` into the legacy payload.
6. Send payload to backend `POST /auth/telegram`.
7. Store `token`, `telegramId`, `userId`, `systemRole` in `chrome.storage.local`.
8. REST requests use `Authorization: Bearer <token>`.
9. STOMP CONNECT uses native header `Authorization: Bearer <token>`.

## External Setup Requirement

Telegram Login requires allowed URLs/domains to be configured in BotFather. For the extension flow, the allowed URL must include the stable Chrome identity redirect origin:

```text
https://<extension-id>.chromiumapp.org
```

For dev, the extension ID should be stable. If needed, add a fixed extension key or document that the current unpacked extension ID must be registered in BotFather.

## Notes

* The bot token must remain backend-only.
* The extension only needs the public bot/client ID (`bot_id`).
* The backend currently implements the legacy widget signature contract, not the newer OIDC `id_token` contract.
