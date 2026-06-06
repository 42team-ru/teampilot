# Move Whisper to LLM Worker

## Goal

Убрать Whisper из Spring-монолита и перенести транскрипцию аудио в LLM Worker (Python).
Spring не вызывает Whisper — только сохраняет файл и публикует `audio.new` в Kafka.
LLM Worker берёт аудио из MinIO, транскрибирует через Whisper REST API, извлекает задачи.
Попутно: очистить модель `UploadedFile` (добавить FK на TeamUser, поля title/description/summary).

## Requirements

### Spring — удалить
- `AudioFile` entity + `AudioFileRepository`
- `AudioController` (REST `/audio/upload`)
- `AudioService`
- `AudioTranscriptService`
- `AudioConverter`
- `WhisperService`
- `WhisperProperties`
- `TranscriptEventPublisher`
- `AudioNewEvent` — **переработать** (см. ниже)
- `KafkaTopics.TRANSCRIPT_READY` — убрать (топик `audio.transcript.ready` больше не нужен)

### Spring — изменить

**`UploadedFile` entity (`uploaded_files` table):**
- Добавить FK `@ManyToOne(nullable=true) TeamUser teamUser` — lookup по `chatId + userId`
- Убрать сырые поля `telegramUserId`, `telegramChatId`, `telegramUsername`, `telegramFirstName` — всё это уже есть в `TeamUser → User` и `TeamUser → Team`
- Добавить nullable поля: `String title`, `String description`, `String summary` (для будущей LLM-генерации)
- Оставить: `bucket`, `s3Key`, `originalFilename`, `contentType`, `sizeBytes`

**`FileUploadConsumer`:**
- После сохранения `UploadedFile` — если `contentType` аудио или видео (`audio/*`, `video/*`): опубликовать `AudioNewEvent` в `audio.new`
- Lookup `TeamUser`: `findByTeam_TelegramChatIdAndUser_TelegramId(chatId, userId)` — если не найден, `teamUser = null`

**`AudioNewEvent` (переработать):**
```java
UUID fileId        // UploadedFile.id
String teamId      // Team.id (из TeamUser.team, если найден, иначе null — резолвим по chatId)
Long teamChatId    // Telegram chatId (для резолва на стороне LLM если teamId null)
String bucket
String s3Key
String originalFilename
String contentType
```

**`TeamUserRepository` (добавить метод):**
```java
Optional<TeamUser> findByTeam_TelegramChatIdAndUser_TelegramId(Long chatId, Long telegramId);
```

### LLM Worker — добавить

**`infra/whisper.py`** — транскрипция через `openai` SDK с переключаемым `base_url`:
- `transcribe(audio_bytes: bytes, filename: str) -> str`
- Использует `openai.OpenAI(base_url=..., api_key=...)` → `client.audio.transcriptions.create()`
- Конфиг из `settings.py`:
  - `WHISPER_API_BASE` (default: `http://localhost:8002/v1`) — whisper.cpp / Groq / OpenAI
  - `WHISPER_API_KEY` (default: `"dummy"`)
  - `WHISPER_MODEL` (default: `"whisper-1"`)
  - `WHISPER_LANGUAGE` (default: `"ru"`)
  - `WHISPER_TIMEOUT_SECONDS` (default: `120`)
- Смена провайдера: только env-переменные, код не трогается

**`infra/audio.py`** — конвертация аудио:
- `to_whisper_wav(audio_bytes: bytes) -> bytes`
- Через `pydub` + `ffmpeg`: 16kHz, mono, PCM 16-bit WAV
- Fallback: если конвертация не удалась — вернуть оригинальные байты

**`models.py`** — добавить `AudioNewEvent`:
```python
class AudioNewEvent(BaseModel):
    file_id: str = Field(alias="fileId")
    team_id: str | None = Field(alias="teamId", default=None)
    team_chat_id: int | None = Field(alias="teamChatId", default=None)
    bucket: str
    s3_key: str = Field(alias="s3Key")
    original_filename: str = Field(alias="originalFilename")
    content_type: str = Field(alias="contentType")
```

**`main.py`** — добавить `run_audio_consumer()`:
- Топик: `audio.new`
- Скачать аудио из MinIO → сконвертировать → транскрибировать → `process_transcript_text(text, team_id)`
- Обработка параллельна существующим consumers

**`processor.py`** — извлечь `process_transcript_text(text, team_id)` из `process_transcript()`:
- `process_transcript()` становится тонкой обёрткой (скачать из S3 → вызвать `process_transcript_text`)
- `run_audio_consumer` вызывает `process_transcript_text` напрямую

### Kafka топики

| Топик | Было | Стало |
|---|---|---|
| `audio.new` | не использовался | Spring → LLM Worker (аудио готово) |
| `audio.transcript.ready` | Spring → LLM Worker | **удалить** |

### Конфиг Spring — убрать

```yaml
app:
  whisper:
    base-url: ...
    endpoint: ...
    model: ...
    language: ...
    timeout-seconds: ...
```

## Acceptance Criteria

- [ ] Spring не содержит `WhisperService`, `AudioTranscriptService`, `AudioConverter`, `AudioFile`, `AudioController`
- [ ] `FileUploadConsumer` публикует `audio.new` для аудио/видео файлов
- [ ] `UploadedFile` содержит FK `teamUser` (nullable), поля `title`/`description`/`summary` (nullable)
- [ ] LLM Worker успешно скачивает аудио из MinIO, конвертирует, транскрибирует через Whisper
- [ ] LLM Worker извлекает задачи из транскрипта аудио
- [ ] Топик `audio.transcript.ready` не используется
- [ ] Spring собирается без ошибок

## Definition of Done

- Spring компилируется, запускается
- LLM Worker запускается, consumer `audio.new` подключается к Kafka
- `pydub` добавлен в `requirements.txt` / `pyproject.toml` LLM Worker

## Out of Scope

- Генерация `title`/`description`/`summary` через LLM (отдельная задача)
- Retry / dead-letter queue для упавших транскрипций
- UI для управления загруженными файлами

## Decision (ADR-lite)

**Context**: Spring вызывал Whisper напрямую через REST, что мешает масштабированию и не вписывается в роль монолита как оркестратора данных (не AI-воркера).  
**Decision**: Whisper переносится в LLM Worker; Spring только сохраняет файл в БД и сигнализирует через Kafka. Для ASR используется `openai` SDK с переключаемым `base_url` — тот же паттерн что LLM chains. Смена провайдера (whisper.cpp → Groq → OpenAI) через env-переменные.  
**Consequences**: LLM Worker требует `openai` SDK + pydub+ffmpeg; UploadedFile получает TeamUser FK вместо сырых telegram-полей. OpenRouter не поддерживает Audio Transcription API — для ASR используем Groq/OpenAI/local.

## Technical Notes

- `Team.telegramChatId` + `TeamRepository.findByTelegramChatId()` — уже есть
- `User.telegramId` — уже есть
- `TeamUser` — даёт team + user + role + position в одной сущности
- `llm-worker/infra/minio.py` — `download_file(bucket, key) → bytes` уже есть
- `llm-worker/settings.py` — `WHISPER_BASE_URL`, `WHISPER_LANGUAGE`, `WHISPER_TIMEOUT_SECONDS` уже есть
- Whisper endpoint format: `POST /inference` (whisper.cpp) или `POST /v1/audio/transcriptions` (OpenAI-compatible)
  — определяется настройкой `WHISPER_ENDPOINT`
