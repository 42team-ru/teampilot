# audio.new enrichment + audio-specific LLM prompt

## Goal

Spring обогащает событие `audio.new` данными команды (members, columns, stickers) прямо при публикации.
LLM Worker получает весь контекст в одном событии и использует отдельный аудио-промпт, адаптированный под речевой транскрипт (нет [ID:], нет авторов, люди обращаются по имени).

## What I already know

- `AudioNewEvent.java`: сейчас содержит только `fileId`, `teamId`, `teamChatId`, `bucket`, `s3Key`, `originalFilename`, `contentType`, `sizeBytes`, `uploadedAt`
- Spring уже имеет все репозитории для обогащения:
  - `teamUserRepository.findByTeamId(UUID)` → список TeamUser с User (telegramId, username, firstName, lastName)
  - `taskColumnRepository.findByTeamId(UUID)` → список TaskColumn
  - `stickerRepository.findByTeamIdWithStates(UUID)` — stickers с states
- Тот же набор данных используется в `ChatMessageBatchPublisher.publishBatch()` — можно переиспользовать логику
- `AudioEventPublisher` уже инжектирует `TeamUserRepository`. Нужно добавить `TaskColumnRepository` и `YouGileStickerRepository`
- Python models `TeamMember`, `ColumnInfo`, `StickerInfo` уже есть в `models.py`
- Функции форматирования `format_team_context`, `format_columns_context`, `format_task_candidates` уже есть в `processor.py`
- Текущий промпт `TASK_SYSTEM` уже обрабатывает отсутствие `[ID:]` (→ `source_message_ids: []`)
- Транскрипт Whisper — сплошной текст без разбивки по спикерам (diarization не включена)
- `teamId` может быть `null` если файл загружен неизвестным пользователем → graceful degradation

## Requirements (evolving)

### Spring
- [ ] Добавить в `AudioNewEvent.java` поля: `List<TeamMemberDto>`, `List<ColumnDto>`, `List<StickerDto>`
- [ ] `AudioEventPublisher.publishAudioNew()` — fetch members/columns/stickers по `team.getId()` и вложить в событие
- [ ] Если `team == null` → пустые списки

### LLM Worker — модель
- [ ] Обновить `AudioNewEvent` в `models.py` добавив `team`, `columns`, `stickers`

### LLM Worker — промпт
- [ ] Написать `AUDIO_TASK_SYSTEM` + `AUDIO_STATUS_SYSTEM` промпты для транскриптов
- [ ] Адаптировать под: нет [ID:], нет авторов, обращение по имени/нику ("Влад, займись")
- [ ] Формат description: `«цитата из транскрипта»` без `«author: »`
- [ ] Отдельные `audio_task_chain` / `audio_status_chain` (структура как у существующих)

### LLM Worker — processor
- [ ] `_process_transcript_chunk()` принимает `team`, `columns`, `stickers` из event
- [ ] Использует `audio_task_chain` и `audio_status_chain` вместо `task_chain`/`status_chain`
- [ ] Статусы: Qdrant-поиск по кандидатам (как в батч-флоу, `search_tasks(chunk, team_id)`)
- [ ] Graceful degradation: если `team_id == null` → пустые контексты, Qdrant не вызывается

## Open Questions

(нет)

## Acceptance Criteria (evolving)

- [ ] `audio.new` event содержит members, columns, stickers
- [ ] LLM Worker корректно десериализует обогащённый event
- [ ] Задачи из транскрипта создаются с правильным `assignee_id` (через name resolution)
- [ ] Graceful degradation при `teamId == null` (пустые контексты)

## Out of Scope

- Speaker diarization (Whisper без диаризации → сплошной текст)
- REST endpoint в Spring для получения контекста

## Technical Notes

- Spring: `AudioEventPublisher` → инжектировать `TaskColumnRepository`, `YouGileStickerRepository`
- Java DTO внутри `AudioNewEvent` можно взять структуру из `ChatMessageBatchPublisher` (те же поля)
- `AudioNewEvent` использует `@Jacksonized @Builder` → можно добавить List-поля с дефолтами
- Python: `models.py` — `AudioNewEvent` уже есть, нужно добавить поля с `default_factory=list`
- Stickers в аудио промпте: менее важны, но данные будут в событии
