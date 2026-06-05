# llm-worker: extract processor.py from main.py

## Goal

Выделить бизнес-логику обработки батчей и транскриптов из `main.py` в отдельный `processor.py`,
чтобы `main.py` содержал только Kafka-loops и точку входа.

## Requirements

- Создать `llm-worker/processor.py` с функциями:
  - `format_messages`, `format_team_context`, `format_columns_context`
  - `resolve_assignee_id`, `_pick_column`, `build_column_map`
  - `_DONE_KEYWORDS`, `_PROGRESS_KEYWORDS`, `_TODO_KEYWORDS`
  - `process_batch`, `_extract_tasks`, `_extract_statuses`
  - `process_transcript`, `_process_transcript_chunk`
- `main.py` оставить только: `_process_and_publish_batch`, `run_transcript_consumer`, `main`, topic-константы
- Публичный API (`process_batch`, `process_transcript`) не меняется
- Никаких изменений логики — только перемещение

## Acceptance Criteria

- [ ] `processor.py` создан, содержит перечисленные функции
- [ ] `main.py` импортирует из `processor.py` и не дублирует логику
- [ ] `debug_run.py` и `tests/runner.py` продолжают работать без изменений

## Out of Scope

- Изменения логики
- Новые абстракции (KafkaWorker, ProcessingContext и т.д.)
- Разбивка на более мелкие модули

## Technical Notes

- `_process_transcript_chunk` публикует в Kafka напрямую — остаётся в processor.py (он уже импортирует kafka)
- Функция `_process_and_publish_batch` завязана на `_process_and_publish_batch` → publish → остаётся в main.py
- Circular import невозможен: processor.py ← main.py (односторонняя зависимость)
