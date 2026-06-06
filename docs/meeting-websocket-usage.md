# Meeting WebSocket Usage

Документ описывает, как клиенту работать с live-meeting flow: REST, auth,
STOMP/WebSocket destinations, payloads и ожидаемые ответы.

## Base URLs

Если клиент ходит напрямую в Spring backend:

```text
HTTP:      http://localhost:8080
WebSocket: ws://localhost:8080/ws
```

Если клиент ходит через Caddy:

```text
HTTP:      https://42team.ru/api
WebSocket: wss://42team.ru/api/ws
```

Caddy снимает `/api` перед проксированием в backend, поэтому backend routes ниже
указаны без `/api`. Для внешнего клиента просто добавляй `/api`.

## Auth

REST endpoints и STOMP CONNECT принимают тот же auth, что уже используется в
backend:

```text
Authorization: Bearer <jwt>
```

JWT выдается ручкой:

```http
POST /auth/telegram
```

Для внутренних/dev-клиентов также работает:

```text
X-Telegram-Id: <telegram_id>
```

Для WebSocket эти значения нужно передавать как STOMP CONNECT native headers, не
в body сообщения.

Пример STOMP CONNECT headers:

```json
{
  "Authorization": "Bearer eyJ...",
  "X-Telegram-Id": "123456789"
}
```

Достаточно одного способа. JWT предпочтительнее.

## REST: создать meeting

Создает привязку Telemost URL к команде. Вызывать может только менеджер команды.
Этот же пользователь становится `primaryRecorder`; только он сможет отправлять
аудиочанки.

```http
POST /meetings
Authorization: Bearer <jwt>
Content-Type: application/json
```

```json
{
  "teamId": "2b0c1f91-3295-48cc-bbaf-4a67501f59a1",
  "meetingUrl": "https://telemost.yandex.ru/j/1234567890"
}
```

Ответ:

```json
{
  "id": "c9cf8b63-9104-4b0b-b349-566e70cc26da",
  "teamId": "2b0c1f91-3295-48cc-bbaf-4a67501f59a1",
  "meetingUrl": "https://telemost.yandex.ru/j/1234567890",
  "primaryRecorderTelegramId": 123456789,
  "active": true,
  "createdAt": "2026-06-07T12:30:00"
}
```

## REST: найти meeting по URL

Используется клиентом, который уже находится на странице Telemost и хочет понять,
прикреплен ли этот митинг к команде.

```http
GET /meetings/by-url?meetingUrl=https%3A%2F%2Ftelemost.yandex.ru%2Fj%2F1234567890
Authorization: Bearer <jwt>
```

Если meeting найден, ответ такой же, как у `POST /meetings`.

Если meeting не найден:

```json
{
  "status": 404,
  "title": "Not Found",
  "detail": "Менеджер ещё не прикрепил этот митинг к команде. Попросите менеджера создать митинг для этой команды.",
  "instance": "/meetings/by-url",
  "traceId": "64f1a2b3c4d5e6f7"
}
```

UI должен показать `detail` пользователю.

## WebSocket/STOMP

Подключение:

```text
CONNECT ws://localhost:8080/ws
```

или через Caddy:

```text
CONNECT wss://42team.ru/api/ws
```

STOMP application prefix:

```text
/app
```

STOMP broker topic prefix:

```text
/topic
```

## Что слушать

Подписка на live output конкретного meeting:

```text
SUBSCRIBE /topic/meetings/{meetingId}/results
```

Пример:

```text
/topic/meetings/c9cf8b63-9104-4b0b-b349-566e70cc26da/results
```

Сообщение от backend:

```json
{
  "meetingId": "c9cf8b63-9104-4b0b-b349-566e70cc26da",
  "teamId": "2b0c1f91-3295-48cc-bbaf-4a67501f59a1",
  "chunkIndex": 7,
  "transcript": "Так, Вова, нужно доделать авторизацию через Telegram...",
  "summary": "Обсудили доработку авторизации и задачу по WebSocket.",
  "context": "Накопленный фрагмент расшифровки, который LLM сейчас использует как контекст.",
  "tasks": [
    {
      "title": "Доработать авторизацию через Telegram",
      "description": "Необходимо исправить...",
      "assigneeId": 123456789,
      "deadline": "2026-06-08T23:59:00Z",
      "columnId": "8e37f1c0-5bcb-4a21-9db9-82b95b626a02",
      "confidence": 0.91
    }
  ],
  "statuses": [
    {
      "taskId": "7ac7e8dd-c439-45b6-b64c-0a507197ce1c",
      "assigneeId": 123456789,
      "columnId": "2bc69cd7-4e5e-43ca-96a4-c0f10dc76212",
      "action": "COMPLETE"
    }
  ]
}
```

Поля `tasks` и `statuses` могут быть пустыми. Это нормально: transcript приходит
на каждый обработанный chunk, а extraction запускается только когда накопилось
достаточно контекста или пришел `finalChunk=true`.

## Куда пушить аудио

Отправка аудиочанка:

```text
SEND /app/meetings/{meetingId}/chunks
```

Пример:

```text
/app/meetings/c9cf8b63-9104-4b0b-b349-566e70cc26da/chunks
```

Payload:

```json
{
  "chunkIndex": 0,
  "audioBase64": "GkXfo59ChoEBQveBAULygQRC84EIQoKI...",
  "contentType": "audio/webm",
  "originalFilename": "meeting-chunk-000000.webm",
  "finalChunk": false
}
```

`audioBase64` может быть чистым base64 или data URL:

```text
data:audio/webm;base64,GkXfo59ChoEBQveBAULygQRC84EIQoKI...
```

Правила:

* `chunkIndex` начинается с `0` и растет на `1`.
* `contentType` по умолчанию считается `audio/webm`, если не передан.
* `finalChunk=true` отправляй последним сообщением, когда запись закончилась.
* Пушить чанки может только `primaryRecorder`, то есть менеджер, который создал meeting.
* Остальные участники могут только слушать `/topic/meetings/{meetingId}/results`.

## Полный сценарий клиента

1. Получить JWT через `/auth/telegram`.
2. На странице Telemost взять текущий URL.
3. Вызвать `GET /meetings/by-url?meetingUrl=<encoded url>`.
4. Если пришел `404`, показать пользователю `detail`: нужно попросить менеджера
   создать meeting.
5. Если meeting найден, подключиться к `/ws` с STOMP CONNECT auth headers.
6. Подписаться на `/topic/meetings/{meetingId}/results`.
7. Если текущий пользователь `primaryRecorder`, начать отправлять аудиочанки в
   `/app/meetings/{meetingId}/chunks`.
8. При завершении записи отправить последний chunk с `finalChunk=true`.

## Internal Kafka Flow

Это не нужно клиенту напрямую, но полезно для debugging:

```text
STOMP chunk
  -> Spring MeetingAudioChunkService
  -> MinIO object meetings/{meetingId}/chunks/{chunkIndex}-...
  -> Kafka meetings.audio.chunks
  -> LLM Worker Whisper + extraction
  -> Kafka llm.tasks.create / llm.status.change
  -> Kafka meetings.live.results
  -> Spring MeetingLiveResultConsumer
  -> STOMP /topic/meetings/{meetingId}/results
```

Internal topics:

```text
meetings.audio.chunks   Spring -> LLM Worker
meetings.live.results   LLM Worker -> Spring
llm.tasks.create        LLM Worker -> Spring task creation
llm.status.change       LLM Worker -> Spring task status updates
```
