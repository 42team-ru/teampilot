# Переделать логику расширения под backend и WebSocket

## Goal

Перевести Chrome extension с моков, polling/SSE-идей и старого POST-upload flow на актуальный backend contract: REST для поиска/создания meeting и STOMP/WebSocket для отправки audio chunks и получения live результатов.

## What I Already Know

* Пользователь просит ориентироваться на `docs`, а если что-то непонятно - смотреть реализацию backend.
* Вложенный старый prompt описывает POST chunks + SSE и прямо запрещает WebSocket, но актуальный запрос пользователя и `docs/meeting-websocket-usage.md` требуют WebSocket/STOMP.
* Backend реализует:
  * `POST /meetings` с `{ teamId, meetingUrl }`;
  * `GET /meetings/by-url?meetingUrl=...`;
  * STOMP endpoint `/ws`;
  * SEND `/app/meetings/{meetingId}/chunks`;
  * SUBSCRIBE `/topic/meetings/{meetingId}/results`.
* Backend требует auth для REST и STOMP CONNECT: `Authorization: Bearer <jwt>` или dev/internal `X-Telegram-Id`.
* Telegram Login Widget/OAuth упёрся в BotFather domain restrictions для Chrome extension.
* Auth для расширения переводится на pairing-code flow: extension создаёт код, пользователь отправляет `/start <code>` боту, бот подтверждает код в backend, extension получает JWT polling-ом.
* Только `primaryRecorder` может отправлять аудиочанки; остальные участники только слушают results topic.
* Current extension is under `extention/` and already uses WXT, React, TypeScript, Tailwind, shadcn-style UI, background service worker and offscreen document.
* Initial inspection found mock API methods in `extention/services/api.ts`; those need to be replaced by real backend calls.
* Initial inspection found `MediaRecorder.start(5000)` in offscreen recording; the backend flow benefits from independent WebM chunks.

## Requirements

* Add Telegram bot code login to the extension and store backend JWT + telegramId.
* Gate popup and sidepanel behind login: before login, only code creation/instructions are available.
* Add a Telegram bot manager flow that creates a backend meeting for a selected team from a call URL and posts that URL to the linked team chat.
* Replace mock meeting/result API in the extension with real backend calls matching `docs/meeting-websocket-usage.md`.
* Use active tab URL as `meetingUrl` for `GET /meetings/by-url`.
* Connect to backend STOMP WebSocket after meeting lookup succeeds.
* Pass `Authorization: Bearer <token>` as REST headers and STOMP native CONNECT headers.
* Subscribe to `/topic/meetings/{meetingId}/results` and store/display live transcript, summary, task candidates and status changes in the sidepanel.
* Send each recorded audio chunk over STOMP to `/app/meetings/{meetingId}/chunks` as JSON with `chunkIndex`, `audioBase64`, `contentType`, `originalFilename`, and `finalChunk`.
* On stop, send the last available chunk/final marker with `finalChunk=true` and close recording resources cleanly.
* Keep audio capture in the offscreen document, not in the MV3 service worker.
* Keep tab audio audible to the user while recording.
* Prefer a vertical slice first: meeting lookup -> STOMP connect -> tab capture -> one self-contained chunk -> STOMP send -> stop/final chunk.

## Acceptance Criteria

* [ ] Extension builds with `npm run compile` and `npm run build` from `extention/`.
* [ ] User can create a six-digit Telegram bot login code from the extension UI.
* [ ] Before login, recording/settings/results controls are not clickable or visible.
* [ ] Bot confirms `/start <code>` through backend `POST /auth/extension-login/{code}/confirm`.
* [ ] Manager can open a team in the bot, enter an http/https call URL, create `POST /meetings`, and send the call link to the linked team chat.
* [ ] Backend JWT and telegramId are stored in extension local storage.
* [ ] Unauthorized Start Recording prompts the user to log in first.
* [ ] Start Recording looks up the active page URL through `GET /meetings/by-url`.
* [ ] If meeting lookup returns backend 404 detail, the UI shows that detail.
* [ ] STOMP connects to `/ws` with the configured auth header.
* [ ] Extension subscribes to `/topic/meetings/{meetingId}/results` and updates sidepanel data from backend messages.
* [ ] Offscreen recording captures tab audio and keeps tab playback audible.
* [ ] Chunks are standalone WebM blobs, base64 encoded, and sent to `/app/meetings/{meetingId}/chunks`.
* [ ] `chunkIndex` starts at `0` and increments by `1`.
* [ ] Stop sends `finalChunk=true`, stops tracks, closes audio context and disconnects STOMP.
* [ ] Old fake data is no longer the main path for meeting results.

## Definition Of Done

* Tests or type-check/build validation run where feasible.
* No unrelated refactors.
* Frontend state and UI naming remain consistent with existing extension screens.
* Backend docs/implementation are treated as the source of truth.

## Technical Approach

Use the current WXT architecture and replace service boundaries:

* New auth service: login code creation/polling, auth storage.
* `services/api.ts`: real REST helpers, backend base URL config, auth header helper.
* New or expanded WebSocket service: STOMP client lifecycle, subscribe/send/disconnect.
* `background.ts`: orchestrates state, meeting lookup, offscreen setup, STOMP connection, chunk forwarding and stop/finalization.
* `offscreen/main.ts`: owns media capture and creates self-contained chunks through a manual recorder loop instead of `MediaRecorder.start(5000)`.
* `types/recording.ts` and `types/messages.ts`: align recording, auth and live result types with backend DTOs.
* `storage.ts`: consider moving shared recording/results state to `chrome.storage.local` so popup and sidepanel stay synchronized across extension surfaces.

Telegram bot code login flow:

* Extension calls `POST /auth/extension-login`.
* Extension stores and displays the returned code.
* User sends `/start <code>` to the configured Telegram bot.
* Bot calls `POST /auth/extension-login/{code}/confirm` with `X-Bot-Secret`.
* Extension polls `GET /auth/extension-login/{code}` and stores JWT when confirmed.
* Configure public `VITE_TELEGRAM_BOT_USERNAME` for the bot username.

Telegram bot manager meeting flow:

* Manager opens a manager-owned team in the bot.
* Bot shows the create-meeting action only when the team has a linked Telegram chat.
* Manager sends an http/https call URL.
* Bot calls `POST /meetings` with `{ teamId, meetingUrl }` and `X-Telegram-Id` set to the manager ID.
* Backend checks manager membership and stores the manager as `primaryRecorder`.
* Bot posts the call URL to the linked Telegram chat after backend creation succeeds.

## Research References

* [`research/backend-websocket-contract.md`](research/backend-websocket-contract.md) - backend REST/STOMP contract verified against docs and code.
* [`research/telegram-oauth-extension.md`](research/telegram-oauth-extension.md) - rejected/legacy option: Telegram OAuth flow for Chrome extension matched to backend auth implementation.

## Decision (ADR-lite)

**Context**: The pasted extension prompt conflicts with current backend docs. It references SSE, POST audio chunk upload, finish endpoint, and confirm/reject task endpoints that do not match the implemented backend meeting flow. The first auth idea was a dev-only `X-Telegram-Id`, then Telegram OAuth, but BotFather rejected Chrome extension redirect domains.

**Decision**: Use `docs/meeting-websocket-usage.md` and backend implementation as source of truth for this task. Implement Telegram bot code login and use the backend JWT for REST and STOMP.

**Consequences**: The implementation will remove or bypass old mock/SSE/polling assumptions. Confirm/reject task UI will not call old nonexistent meeting task endpoints in this MVP unless a matching backend route is discovered or added. Pending login codes are temporary and may be invalidated by backend restart.

## Out Of Scope

* New Telegram OIDC `id_token` backend flow; current backend uses legacy Telegram Login Widget signature payload.
* Video capture.
* WebRTC.
* Meeting history/dashboard.
* Backend route changes unless the extension cannot work against the existing contract.
* Old SSE endpoint support.
* Old POST `/api/meetings/{meetingId}/chunks` upload support.
* Old `/api/meetings/{meetingId}/finish` support.
* Old `/api/meetings/{meetingId}/tasks/{taskId}/confirm|reject` support.

## Technical Notes

* Direct backend base: `http://localhost:8080`; direct WS: `ws://localhost:8080/ws`.
* Caddy base: `https://42team.ru/api`; Caddy WS: `wss://42team.ru/api/ws`.
* Backend routes in code do not include `/api`; frontend config should allow both direct and proxied bases.
* STOMP dependency is not currently present in `extention/package.json`; likely add `@stomp/stompjs`.
* Current package path is spelled `extention`, not `extension`.
