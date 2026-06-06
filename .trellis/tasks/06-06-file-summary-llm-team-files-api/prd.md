# File Summary via LLM + Team Files API + Bot

## Goal

После того как LLM Worker расшифровывает аудио/видео файл командной встречи через Whisper,
нужно (1) сгенерировать title/description/summary файла через LLM и сохранить в БД,
(2) добавить REST-эндпоинт для просмотра файлов команды с presigned URL,
(3) отобразить файлы в боте.

## What I already know

* `UploadedFile` (entity) уже имеет поля `title VARCHAR(500)`, `description VARCHAR(2000)`, `summary TEXT` — они никогда не заполняются
* `UploadedFileRepository` имеет `findByTeamUser_Team_TelegramChatId(Long chatId)` — можно выбрать файлы команды
* `TranscriptReadyEvent` существует в `kafka-common` но топик не объявлен в `KafkaTopics`
* LLM Worker: `process_audio()` → `transcribe()` → `process_transcript_text()` (только задачи); summary не генерируется
* Все LLM промпты в `llm/prompts.py`, chains в `llm/chains.py`
* Kafka публикация в LLM Worker через `infra/kafka.py::publish(topic, event, key)`
* Spring events: `AudioNewEvent` → `audio.new` топик; аналогично нужен новый `files.transcript_ready`
* `s3Service.presignedGetUrl(bucket, key, Duration)` доступен через `S3Service`
* `TeamController` уже имеет `/{teamId}/members` — логично добавить `/{teamId}/files` туда же
* Bot: `services/team_service.py` делает REST-вызовы к Spring; handlers в `bot/handlers/`
* `FileUploadStates` и `upload.py` handler — паттерн для FSM-состояний бота

## Requirements

1. **LLM Worker**: после транскрипции добавить LLM-цепочку для генерации `title` (до 100 символов), `description` (2-4 предложения), `summary` (резюме встречи, 5-10 предложений) из текста транскрипта
2. **LLM Worker**: публиковать новый Kafka-ивент `files.transcript_ready` с `fileId`, `teamId`, `title`, `description`, `summary`
3. **Spring**: добавить топик `FILES_TRANSCRIPT_READY = "files.transcript_ready"` в `KafkaTopics`
4. **Spring**: Kafka consumer читает `files.transcript_ready` → обновляет `UploadedFile.title/description/summary`
5. **Spring**: REST `GET /teams/{teamId}/files` — список файлов команды (только участники команды могут просматривать); каждый файл возвращает presigned download URL (15 минут TTL)
6. **Bot**: команда/кнопка "📁 Файлы" в контексте команды → список файлов с title (или filename если title нет), summary (если есть), кнопкой скачивания (presigned URL)

## Acceptance Criteria

* [ ] После загрузки аудио/видео файла в команду, в БД заполняются `title`, `description`, `summary`
* [ ] `GET /teams/{teamId}/files` возвращает список файлов с presigned URL
* [ ] Бот показывает список файлов команды с AI-сгенерированным title/summary
* [ ] Если summary ещё не готов (LLM не успел) — показывается только filename

## Definition of Done

* Тесты: unit-тест на LLM prompt (mock), integration-тест на Spring consumer
* Lint / typecheck: mypy/ruff для Python, javac для Spring
* Нет N+1 запросов в endpoint файлов

## Technical Approach

### LLM Worker (Python)

Новый промпт `FILE_SUMMARY_SYSTEM` в `prompts.py`:
```
Ты ИИ-ассистент. Тебе дан транскрипт встречи IT-команды.
Сгенерируй:
- title: до 100 символов, ёмкое название встречи
- description: 2-4 предложения, о чём встреча
- summary: резюме встречи 5-10 предложений с ключевыми решениями
Ответ ТОЛЬКО JSON: {"title": "...", "description": "...", "summary": "..."}
```

Новый топик Kafka: `files.transcript_ready`

Новый Pydantic-model `FileSummaryEvent(BaseModel)` с полями `file_id`, `team_id`, `title`, `description`, `summary`

В `process_audio()`: после `process_transcript_text()` вызвать `generate_file_summary(text, file_id, team_id)`

### Spring (Java)

Новый топик в `KafkaTopics`:
```java
public static final String FILES_TRANSCRIPT_READY = "files.transcript_ready";
```

Новый consumer `FileSummaryConsumer`:
```java
@KafkaListener(topics = KafkaTopics.FILES_TRANSCRIPT_READY)
public void consume(FileSummaryEvent event) {
    fileUploadService.updateSummary(event.getFileId(), event.getTitle(), event.getDescription(), event.getSummary());
}
```

`FileUploadService.updateSummary()` — `@Transactional`, обновляет поля в entity.

New DTO `UploadedFileResponse`: `id`, `originalFilename`, `title`, `description`, `summary`, `contentType`, `sizeBytes`, `createdAt`, `downloadUrl`

Endpoint: `GET /teams/{teamId}/files` — добавить в `TeamController` (рядом с `/{teamId}/members`)

Авторизация: проверять что текущий пользователь — участник команды (через `TeamUserRepository.existsByTeamIdAndUserTelegramId`)

### Bot (Python)

Новый `service` метод `get_team_files(team_id)` → `GET /teams/{teamId}/files`

Новый handler: кнопка "📁 Файлы" в меню члена команды → список файлов

Формат сообщения:
```
📁 <title или filename>
📝 <description или "-">
📋 <summary (первые 200 символов)>
⬇️ Скачать
```

## Decision (ADR-lite)

**Context**: нужно добавить LLM-генерацию summary для файлов и отобразить их в боте  
**Decision**: отдельный Kafka топик `files.transcript_ready`, новый LLM chain в worker, REST endpoint в TeamController  
**Consequences**: минимальное изменение существующего кода; асинхронно — summary появляется после обработки LLM

## Out of Scope

* Пагинация файлов (список небольшой для хакатона)
* Генерация summary для не-аудио файлов
* Редактирование title/description вручную
* Поиск по файлам

## Technical Notes

* `AbstractStoredFileEntity` имеет `bucket`, `s3Key`, `originalFilename`, `contentType`, `sizeBytes`
* `S3Service.presignedGetUrl(bucket, key, Duration.ofMinutes(15))` — доступен через DI
* LLM Worker `infra/kafka.py::publish(topic, event, key)` — уже используется для задач
* `models.py` в LLM Worker определяет Pydantic-модели событий
* `llm/chains.py` — паттерн для новой LLM chain
* `bot/services/team_service.py` — паттерн для новых REST-вызовов
