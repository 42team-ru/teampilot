# Backend WebSocket Contract Research

## Sources

* `docs/meeting-websocket-usage.md`
* `backend/monolith/src/main/java/ru/team42/monolith/rest/MeetingController.java`
* `backend/monolith/src/main/java/ru/team42/monolith/websocket/MeetingWebSocketController.java`
* `backend/monolith/src/main/java/ru/team42/monolith/config/WebSocketConfig.java`
* `backend/monolith/src/main/java/ru/team42/monolith/websocket/WebSocketAuthChannelInterceptor.java`
* `backend/monolith/src/main/java/ru/team42/monolith/service/MeetingAudioChunkService.java`
* `backend/monolith/src/main/java/ru/team42/monolith/dto/response/MeetingLiveResultResponse.java`

## REST Contract

The current backend exposes meeting routes without an `/api` prefix when called directly:

* `POST /meetings` with `{ teamId, meetingUrl }`, authenticated manager only. The creator becomes `primaryRecorder`.
* `GET /meetings/by-url?meetingUrl=<encoded>` to find the active meeting by URL.

When accessed through Caddy, external clients use `https://42team.ru/api`, while Caddy strips `/api` before Spring.

## Auth Contract

REST and STOMP CONNECT both accept:

* `Authorization: Bearer <jwt>`
* or dev/internal `X-Telegram-Id: <telegram_id>`

For STOMP, these must be native CONNECT headers, not message payload fields.

## STOMP Contract

Backend endpoint:

* WebSocket endpoint: `/ws`
* Application prefix: `/app`
* Broker topic prefix: `/topic`

Client sends chunks to:

* `/app/meetings/{meetingId}/chunks`

Payload shape:

```json
{
  "chunkIndex": 0,
  "audioBase64": "...",
  "contentType": "audio/webm",
  "originalFilename": "meeting-chunk-000000.webm",
  "finalChunk": false
}
```

Client subscribes to:

* `/topic/meetings/{meetingId}/results`

Result shape:

```json
{
  "meetingId": "uuid",
  "teamId": "uuid-string",
  "chunkIndex": 7,
  "transcript": "...",
  "summary": "...",
  "context": "...",
  "tasks": [],
  "statuses": []
}
```

`tasks` and `statuses` can be empty. `transcript` is expected per processed chunk; extraction may lag until enough context or final chunk arrives.

## Extension Delta

The current extension still has mock API methods and polling:

* `extention/services/api.ts` returns fake meetings/results.
* `extention/entrypoints/background.ts` starts a mock meeting, uploads chunks through the mock service, calls mock finish, and polls fake results.
* `extention/entrypoints/offscreen/main.ts` uses `mediaRecorder.start(5000)`, which can produce chunk fragments that are not independent WebM files.
* `extention/services/storage.ts` uses `chrome.storage.session`; the original extension prompt asked for state shared through local storage.

The implementation should replace mock/polling/SSE assumptions with the documented REST + STOMP flow.

## Recommended MVP Direction

1. Use the backend documentation and implementation as source of truth.
2. Treat the pasted SSE/confirm-reject prompt as outdated where it conflicts with backend docs.
3. Start from a vertical slice:
   * read active tab URL;
   * authenticate with a configured auth header;
   * call `GET /meetings/by-url`;
   * connect STOMP;
   * subscribe to live results;
   * capture tab audio in offscreen;
   * emit self-contained WebM chunks;
   * send chunk JSON over STOMP;
   * send one final STOMP chunk with `finalChunk=true` on stop.
4. Keep old task confirm/reject endpoints out of MVP unless backend routes are added later.
