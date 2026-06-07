# Fix meeting audio chunk duration + re-extract tasks from full transcript

## Goal

1. Увеличить размер аудио-чанка с 2 секунд до 30 секунд (уже сделано).
2. После того как `_finalize_meeting_recording` вернёт полный Whisper-транскрипт — повторно запустить LLM-извлечение задач на полном тексте, чтобы поймать задачи, которые могли пропустить на уровне 2-секундных чанков.

## Requirements

* [x] `CHUNK_DURATION_MS = 30_000` в `extention/entrypoints/offscreen/main.ts` — DONE
* [ ] После успешной `_finalize_meeting_recording`, если `finalization.full_transcript` не пустой — повторно вызвать `_process_transcript_chunk` на полном транскрипте
* [ ] Новые события (задачи/статусы) из полного транскрипта смёрджить с уже извлечёнными из чанков (избегать дублей через `_filter_new_meeting_events`)
* [ ] Новые задачи опубликовать в Kafka через `_publish_transcript_events`
* [ ] `tasks` и `statuses` в финальном `MeetingLiveResultEvent` должны содержать все найденные события (из чанков + из полного транскрипта)

## Acceptance Criteria

* [ ] `CHUNK_DURATION_MS = 30_000` (уже выполнено)
* [ ] При `final_chunk=True` и непустом `finalization.full_transcript` — LLM ищет задачи в полном тексте
* [ ] Дублей задач нет (фильтрация через `_filter_new_meeting_events`)
* [ ] Лог показывает суммарное количество задач из обоих этапов

## Definition of Done

* Изменения только в `llm-worker/processor.py`
* Логика не ломает существующий поток чанков

## Technical Approach

В `process_meeting_audio` (processor.py:946), после блока:
```python
if event.final_chunk:
    finalization = _finalize_meeting_recording(event)
    if finalization is not None:
        transcript = finalization.full_transcript
        ...
```

Добавить: если `finalization` успешна и `finalization.full_transcript` непустой — вызвать `_process_transcript_chunk(finalization.full_transcript, ...)`, затем `_filter_new_meeting_events`, затем `_publish_transcript_events` для новых. Объединить с `extracted_events`.

`_filter_new_meeting_events` уже хранит состояние опубликованных задач по `meeting_id` — повторный вызов автоматически отдедуплицирует.

## Out of Scope

* Изменения в extention / Spring
* Изменение схемы `MeetingLiveResultEvent`

## Technical Notes

* Целевой файл: `llm-worker/processor.py`
* Ключевые функции:
  - `process_meeting_audio` (строка ~946) — основная точка изменений
  - `_finalize_meeting_recording` (строка ~854) — возвращает `MeetingFinalizationResult` с `full_transcript`
  - `_process_transcript_chunk` (строка ~503) — LLM-классификация и извлечение
  - `_filter_new_meeting_events` — дедупликация по meeting_id
  - `_publish_transcript_events` — публикация в Kafka
* `CHUNK_DURATION_MS` изменён: `extention/entrypoints/offscreen/main.ts:3`
