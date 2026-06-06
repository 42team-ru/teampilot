# Добавить confidence score в description задачи из LLM воркера

## Goal

После генерации задачи LLM воркером добавлять в конец description строку с уверенностью классификатора, чтобы в YouGile было видно насколько ИИ уверен в задаче.

## What I already know

- `_extract_tasks(batch, text, confidence)` в `processor.py:109` получает confidence от классификатора
- `_process_transcript_chunk` использует `clf.confidence_task` как confidence для аудио задач
- description генерируется LLM, затем попадает в `task_data["description"]`
- `TaskCreateEvent.confidence: float` уже существует — это поле уходит в Kafka, но нигде не отображается пользователю
- Нужно дописать confidence в конец description ПОСЛЕ генерации LLM, в `processor.py`

## Requirements

- В `_extract_tasks`: после `task_data = extraction.model_dump()` дописывать confidence в `task_data["description"]`
- В `_process_transcript_chunk`: аналогично для аудио задач
- Формат: `\n\nУверенность ИИ: 87%` (округлить до целых, русский текст)
- Только если confidence > 0

## Acceptance Criteria

- [ ] description задачи из батча содержит строку `Уверенность ИИ: XX%`
- [ ] description задачи из аудио транскрипта содержит строку `Уверенность ИИ: XX%`
- [ ] confidence 0.0 — строка не добавляется

## Out of Scope

- Изменения в Spring / БД схеме
- Изменения в промптах

## Technical Notes

- Файл: `llm-worker/processor.py`
- Функции: `_extract_tasks` (line ~122), `_process_transcript_chunk` (line ~265)
