# strict-status-prompt-and-better-logging

## Goal

1. Status extraction слишком агрессивно интерпретирует косвенные сообщения ("Деплой на стейджинг готов, проверяйте") как смену статуса задач. Нужно ужесточить prompt.
2. Логирование не даёт понять что происходит: какая задача создана/пропущена/куда переехала.

## Root Cause (status bug)

В `STATUS_SYSTEM` `<action_types>` слишком широкие сигналы:
- "проверяй", "задеплоено" → COMPLETE: срабатывает на "Деплой на стейджинг готов, проверяйте" (general announcement)
- Нет правила: статус-изменение должно ЯВНО ссылаться на конкретную задачу по имени ИЛИ быть личным отчётом ("я сделал X", "взял X на себя")
- Нет negative примера: общие объявления без упоминания задачи → []

## What I already know

* `llm/prompts.py` → `STATUS_SYSTEM`: action_types + rules + examples
* `processor.py` → `_extract_statuses()`: вызывает `status_chain`, логирует только `event.action`
* `processor.py` → `_extract_tasks()`: логирует только title при пропуске дубликата
* `main.py` → `_process_and_publish_batch()`: логирует только "published"

## Requirements

### Prompt (STATUS_SYSTEM)
* Добавить правило: status change ОБЯЗАН содержать явную ссылку на задачу по названию/теме ИЛИ личный отчёт автора сообщения ("я сделал X", "взял X", "закончил X")
* Добавить правило: общие объявления без привязки к задаче ("деплой готов", "стейджинг проверяйте", "авторизацию закрыли" без контекста задачи) → вернуть []
* Добавить negative example: batch с "Деплой на стейджинг готов, проверяйте" + task candidates → []
* Добавить negative example: повторные сообщения с постановкой задач без явного статус-глагола → []

### Logging
* `_extract_tasks`: INFO с title, assignee_id, deadline, column_id, confidence для каждой созданной задачи
* `_extract_tasks`: INFO при пропуске дубликата (уже есть — оставить)
* `_extract_statuses`: INFO с task_id, action, column_id, assignee_id для каждого статуса
* `_process_and_publish_batch` (`main.py`): итоговый INFO: "Batch {id}: {N} tasks, {M} statuses, {K} skipped as duplicates"

## Acceptance Criteria

* [ ] "Деплой на стейджинг готов, проверяйте" в батче без явной ссылки на задачу → status extraction возвращает []
* [ ] Повторная отправка batch с task-сообщениями (без "сделал/взял/закончил") → status extraction возвращает []
* [ ] Лог содержит для каждой задачи: title, assignee_id, deadline, column_id
* [ ] Лог содержит для каждого статуса: task_id, action, column_id
* [ ] Итоговая строка батча: "Batch X: N tasks, M statuses, K duplicates skipped"

## Technical Notes

* `llm/prompts.py` — STATUS_SYSTEM prompt
* `llm-worker/processor.py` — `_extract_tasks`, `_extract_statuses`
* `llm-worker/main.py` — `_process_and_publish_batch`
