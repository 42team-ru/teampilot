# llm-worker: объединить дублирующиеся модели и вынести meeting логику

## Goal

Два точечных рефакторинга без изменения поведения:
1. Объединить дублирующиеся Pydantic-модели (Audio* vs обычные) и схлопнуть дублирующиеся форматировщики
2. Вынести meeting-логику из processor.py (~300 строк) в отдельный meeting_processor.py

## What I already know

### Дублирующиеся модели (models.py)

| Audio-версия | Обычная | Разница |
|---|---|---|
| `AudioTeamMember` | `TeamMember` | Audio имеет camelCase aliases + defaults для username/full_name/role |
| `AudioColumnInfo` | `ColumnInfo` | Идентичны |
| `AudioStickerState` | `StickerStateInfo` | Идентичны |
| `AudioStickerInfo` | `StickerInfo` | Идентичны (модulo внутренний тип) |

`AudioTeamMember` отличается от `TeamMember` тремя вещами:
- `model_config = ConfigDict(populate_by_name=True)` — нужно для JSON-десериализации
- Field aliases: `telegramId`, `fullName` — нужны для JSON от Spring
- Defaults: `username=""`, `full_name=""`, `role=""` — нужны т.к. JSON может не содержать эти поля

`TeamMember` строится через proto (keyword args, snake_case), aliases не нужны, но не мешают.

### Дублирующиеся форматировщики (processor.py)

| Batch-версия | Audio-версия |
|---|---|
| `format_team_context(batch)` → берёт `batch.team: list[TeamMember]` | `format_audio_team_context(members: list[AudioTeamMember])` |
| `format_columns_context(batch)` → берёт `batch.columns: list[ColumnInfo]` | `format_audio_columns_context(columns: list[AudioColumnInfo])` |
| `format_stickers_context(batch)` → берёт `batch.stickers: list[StickerInfo]` | `format_audio_stickers_context(stickers: list[AudioStickerInfo])` |

Batch-версии принимают весь `MessageBatchEvent`, audio-версии — явные списки.

### Meeting-логика в processor.py (строки ~737–1185)

Функции:
- `MeetingTranscriptState`, `MeetingFinalizationResult` — dataclasses
- `_meeting_state`, `_meeting_state_lock` — глобальный state
- `_meeting_context_after_chunk`, `_meeting_full_context`
- `_meeting_chunks_prefix`, `_chunk_index_from_key`, `_meeting_chunk_object_keys`, `_wait_for_meeting_chunk_objects`
- `_mark_meeting_final_extract`, `_filter_new_meeting_events`
- `_summarize_meeting_context`, `_generate_meeting_final_summary`, `_extract_meeting_speaker_segments`
- `_finalize_meeting_recording`, `process_meeting_audio`
- `_to_meeting_task_preview`, `_to_meeting_status_preview`

Зависимости из meeting-логики:
- `_process_transcript_chunk` (остаётся в processor.py, sharing)
- `_publish_transcript_events` (остаётся в processor.py, sharing)
- `search_tasks` из qdrant
- `store_knowledge` из qdrant
- LLM chains: `file_summary_chain`, `speaker_segments_chain`
- Models: `TaskCreateEvent`, `StatusChangeEvent`, `MeetingAudioChunkEvent`, `MeetingLiveResultEvent`, etc.

## Requirements

1. **Модели**: удалить `AudioTeamMember`, `AudioColumnInfo`, `AudioStickerState`, `AudioStickerInfo`; обновить `TeamMember` (добавить aliases + defaults), `ColumnInfo`/`StickerStateInfo`/`StickerInfo` (без изменений — уже совпадают)
2. **Форматировщики**: batch-версии переписать чтобы принимали явные списки (как audio-версии), audio-версии удалить; места вызова обновить (`batch.team`, `batch.columns`, `batch.stickers`)
3. **Meeting логика**: вынести ~300 строк в `meeting_processor.py`; `processor.py` импортирует только `process_meeting_audio`
4. **Поведение не меняется**: никаких изменений в LLM-вызовах, Kafka-топиках, форматах событий

## Acceptance Criteria

- [ ] `models.py` не содержит Audio-дублей: `AudioTeamMember`, `AudioColumnInfo`, `AudioStickerState`, `AudioStickerInfo`
- [ ] `processor.py` не содержит `_meeting_*` функций и `MeetingTranscriptState`/`MeetingFinalizationResult`
- [ ] Файл `meeting_processor.py` создан и содержит перенесённую логику
- [ ] `main.py` импортирует `process_meeting_audio` из нового места
- [ ] Приложение запускается без ошибок (import check)

## Definition of Done

- Lint / import check зелёный
- Поведение не изменилось (smoke test: python -c "from processor import process_batch; from meeting_processor import process_meeting_audio")

## Out of Scope

- Рефакторинг consumer loops в main.py
- Изменение логики обработки (prompts, chains, threshold'ы)
- Добавление тестов (хакатон, нет тестов)
- Изменение форматов Kafka-событий

## Technical Notes

- `_process_transcript_chunk` и `_publish_transcript_events` нужны и batch-пути и meeting-пути → остаются в processor.py, meeting_processor.py импортирует их
- `AudioNewEvent`, `MeetingAudioChunkEvent` уже используют camelCase aliases → остаются без изменений (это события, не модели команды)
- `MessageBatchEvent` содержит `team: list[TeamMember]` — после переименования тип обновится автоматически

## Open Questions

(нет — всё выводимо из кода)
