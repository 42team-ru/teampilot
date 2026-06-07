# Extension Integrations

## Scenario: Telegram Bot Code Login + Meeting WebSocket In Chrome Extension

### 1. Scope / Trigger

- Trigger: Chrome extension features that authenticate against the Spring backend and stream meeting audio/results through WebSocket/STOMP.
- Applies to WXT MV3 extension code under `extention/`, Spring auth code under `backend/monolith/`, and bot `/start <code>` handling under `bot/`.
- Also applies when the Telegram bot creates a meeting for a manager and posts the call link to the team's linked Telegram chat.
- Backend implementation and `docs/meeting-websocket-usage.md` are the source of truth for meeting routes and STOMP payloads.

### 2. Signatures

- Create extension login code: `POST /auth/extension-login`
- Poll extension login status: `GET /auth/extension-login/{code}`
- Bot confirms code: `POST /auth/extension-login/{code}/confirm`
- Bot creates manager meeting: `POST /meetings`
- Meeting lookup REST: `GET /meetings/by-url?meetingUrl=<encoded-url>`
- STOMP connect endpoint: `/ws`
- STOMP send destination: `/app/meetings/{meetingId}/chunks`
- STOMP subscribe destination: `/topic/meetings/{meetingId}/results`
- Extension audio chunk cadence: record/send one standalone WebM chunk about every `15_000 ms`.
- Backend WebSocket/STOMP text message limit: must be high enough for base64 JSON audio chunks; current target is `4 MiB`.

### 3. Contracts

Environment keys:

- `VITE_API_BASE_URL`: HTTP backend base, e.g. `http://localhost:8080` or `https://42team.ru/api`.
- `VITE_WS_URL`: explicit STOMP WebSocket URL, e.g. `ws://localhost:8080/ws`.
- `VITE_TELEGRAM_BOT_USERNAME`: public bot username without `@`, e.g. `prorab_bot`.
- Backend and bot must share `BOT_SECRET`/`app.bot.secret` for bot-only confirm calls.

Extension login start response:

```json
{
  "code": "123456",
  "expiresAt": "2026-06-07T12:30:00Z"
}
```

Bot confirm request:

```json
{
  "telegramId": 123456789,
  "telegramLogin": "ivan",
  "firstName": "Ivan",
  "lastName": "Petrov"
}
```

Extension status response:

```json
{
  "status": "pending | confirmed | expired",
  "code": "123456",
  "expiresAt": "2026-06-07T12:30:00Z",
  "auth": {
    "userId": "uuid",
    "telegramId": 123456789,
    "systemRole": "USER",
    "token": "jwt"
  }
}
```

Bot manager meeting create request:

```json
{
  "teamId": "uuid",
  "meetingUrl": "https://telemost.yandex.ru/j/1234567890"
}
```

Bot manager meeting create response:

```json
{
  "id": "uuid",
  "teamId": "uuid",
  "meetingUrl": "https://telemost.yandex.ru/j/1234567890",
  "primaryRecorderTelegramId": 123456789,
  "active": true,
  "createdAt": "2026-06-07T12:30:00"
}
```

STOMP audio chunk payload:

```json
{
  "chunkIndex": 0,
  "audioBase64": "...",
  "contentType": "audio/webm",
  "originalFilename": "meeting-chunk-000000.webm",
  "finalChunk": false
}
```

### 4. Validation & Error Matrix

- Missing auth session -> render an auth-only gate; do not expose recording, settings, result tabs, or controls.
- Login code expired -> clear pending challenge and show a user-facing message.
- Bot confirm without `X-Bot-Secret` -> forbidden by `@PreAuthorize("hasRole('BOT')")`.
- Bot `/start` payload is not exactly six digits -> let existing join/link/setup handlers process it.
- Bot meeting creation must send `X-Telegram-Id` for the manager; backend checks `requireManagerMembership(teamId, telegramId)`.
- Bot meeting URL must be non-empty http/https and no longer than backend `@Size(max = 1024)`.
- Team has no linked Telegram chat -> do not show or do not proceed with the bot "create meeting and send link" action.
- Telegram send to group fails after backend meeting creation -> keep the meeting and report to manager that posting the link failed.
- Meeting lookup 404 -> show backend `detail`; do not create a fake meeting.
- `primaryRecorderTelegramId` differs from logged-in Telegram ID -> block upload.
- WebSocket closes with code `1009` -> audio chunk/STOMP text frame is too large; reduce chunk duration/bitrate or raise backend WebSocket transport/container limits.
- WebSocket not connected while publishing chunk -> move recording state to error.
- Unsupported `MediaRecorder` MIME -> show recording error before streaming.

### 5. Good/Base/Bad Cases

- Good: Extension creates a short-lived code, shows `/start <code>`, bot confirms via backend, extension polls until it receives JWT, then connects STOMP with `Authorization: Bearer <token>`.
- Good: Manager opens a team in the bot, enters a call URL, bot creates `POST /meetings` with the manager Telegram ID, then posts the same URL to the linked Telegram chat.
- Base: Extension has no auth session; only code creation/login instructions are clickable.
- Bad: Extension depends on Telegram Login Widget domain configuration, bot creates meetings as `ROLE_BOT` instead of manager `X-Telegram-Id`, frontend stores bot token, or chunks use old mock/POST/SSE paths.
- Bad: Backend keeps default WebSocket text buffer limits while the extension sends base64 audio JSON over STOMP; the session closes as `1009`.

### 6. Tests Required

- Type-check/build must pass: `npm run compile`, `npm run build` in `extention/`.
- Backend compile/test must pass for auth DTO/service/controller changes.
- Bot syntax/import check should pass for new service/handler.
- Bot manager meeting flow:
  - Team context shows the create-meeting action only when a Telegram chat is linked.
  - Invalid meeting URLs are rejected before calling backend.
  - `POST /meetings` contains `teamId`, `meetingUrl`, and `X-Telegram-Id`.
  - Bot posts the call URL to the linked chat after backend confirms creation.
- Manual integration test with backend + bot:
  - Extension receives a six-digit login code.
  - `/start <code>` in bot confirms the code.
  - Extension poll receives JWT and telegramId.
  - Meeting lookup uses current tab URL.
  - STOMP CONNECT includes Authorization header.
  - A recorded chunk reaches `/app/meetings/{meetingId}/chunks`.
  - `/topic/meetings/{meetingId}/results` updates sidepanel storage/UI.

### 7. Wrong vs Correct

#### Wrong

```text
extension -> Telegram Login Widget -> chromiumapp.org redirect
```

This requires BotFather domain configuration and fails for unpacked/dev extension IDs.

#### Correct

```text
extension -> POST /auth/extension-login -> code 123456
user -> bot: /start 123456
bot -> POST /auth/extension-login/123456/confirm
extension -> GET /auth/extension-login/123456 -> JWT
manager -> bot team menu -> create meeting URL
bot -> POST /meetings with X-Telegram-Id
bot -> linked team chat: call URL
extension -> GET /meetings/by-url?meetingUrl=<same URL>
```

> Warning: login codes are short-lived and stored in backend memory. Restarting backend invalidates pending codes.
