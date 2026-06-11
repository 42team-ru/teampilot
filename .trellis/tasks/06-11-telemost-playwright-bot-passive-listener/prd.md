# PRD: Telemost Playwright Bot — Passive Listener

## Цель

Python + Playwright бот, который заходит на звонок Yandex Telemost, записывает аудио чанками и отправляет их в существующий пайплайн LLM Worker через Kafka — аналогично тому, как расширение отправляет батчи сообщений.

---

## User Flow

1. Пользователь пишет в Telegram: `/join https://telemost.yandex.ru/j/...`
2. Бот отвечает сообщением с двумя inline-кнопками:
   - **[🤖 Подключить TeamPilot]** — бот заходит на звонок через Playwright
   - **[🖥 Через расширение]** — существующий флоу, без изменений
3. При выборе TeamPilot:
   - Бот заходит на звонок через Playwright + headless Chrome
   - В звонке бот пишет в чат (или говорит через TTS): _"TeamPilot подключился и записывает встречу"_
   - Начинает запись аудио 30-секундными чанками
   - Каждый чанк: upload в MinIO → публикация в `audio.new` с `source: TELEMOST_BOT`
4. Расширение в режиме TeamPilot:
   - **Не записывает аудио** (теряет статус primary)
   - Только получает уведомления о новых задачах (`bots.tasks`)

---

## Архитектура

```
Telegram Bot
  /join <url> → inline keyboard [TeamPilot | Расширение]
      ↓ выбор TeamPilot
  POST /meetings/join {url, team_id, chat_id}
      ↓
Spring: создаёт Meeting{id, url, status=ACTIVE, source=BOT}
      ↓ publishes meeting.joined → Extension (через WS или push)
Extension: видит meeting.joined → отписывается от записи аудио

Python Bot (Playwright)
  → headless Chrome + PulseAudio virtual sink
  → заходит на Telemost по URL
  → sounddevice читает virtual sink
  → 30-сек чанки → MinIO upload
  → Kafka: audio.new {meeting_id, minio_key, source: "BOT", chunk_index}
      ↓
LLM Worker (без изменений)
  → Groq Whisper → транскрипт
  → LLM → llm.tasks.create / llm.status.change
      ↓
Spring → YouGile + bots.tasks → Telegram уведомления
```

---

## Как расширение узнаёт, что бот записывает

Spring при старте бота публикует событие в существующий WebSocket канал расширения:

```json
{
  "type": "MEETING_BOT_JOINED",
  "meetingUrl": "https://telemost.yandex.ru/j/...",
  "meetingId": "uuid"
}
```

Расширение уже держит WebSocket соединение для получения `bots.tasks` — переиспользуем тот же канал. При получении `MEETING_BOT_JOINED` расширение:
- Не становится primary recorder
- Продолжает показывать задачи (bots.tasks как обычно)

При выходе бота из звонка Spring публикует `MEETING_BOT_LEFT` — расширение может снова стать primary если нужно.

---

## Новые компоненты

### Python Bot (новый сервис `telemost-bot/`)
```
telemost-bot/
  main.py              — Telegram handlers + inline keyboard
  playwright_runner.py — запуск Chrome, вход на звонок
  audio_chunker.py     — sounddevice → 30-сек WAV чанки
  minio_uploader.py    — upload чанка
  kafka_producer.py    — публикация audio.new
  config.py
```

### Spring (минимальные изменения)
- Новый endpoint: `POST /meetings/join` — создать Meeting entity, стартует бота
- Meeting entity: `{id, url, teamId, status, recorderType: BOT|EXTENSION}`
- WebSocket: при старте бота → push `MEETING_BOT_JOINED`, при выходе → `MEETING_BOT_LEFT`

### Kafka (новые топики не нужны)
- `audio.new` — переиспользуем, добавляем поле `source`

---

## Scope MVP

- [ ] Telegram `/join` команда + 2 кнопки
- [ ] Playwright: зайти на Telemost, нажать "разрешить микрофон"
- [ ] PulseAudio virtual sink + sounddevice запись
- [ ] 30-секундные WAV чанки → MinIO → audio.new
- [ ] Spring: Meeting entity + 2 REST endpoints
- [ ] Расширение: polling `/meetings/active`, не пишет аудио если recorder=BOT

## Out of scope (Task 2)
- Wake word / Q&A режим
- TTS ответы в звонке

---

## Стек
- Python 3.12, playwright, sounddevice, confluent-kafka, boto3
- PulseAudio (Linux)
- Spring добавляет Meeting entity
