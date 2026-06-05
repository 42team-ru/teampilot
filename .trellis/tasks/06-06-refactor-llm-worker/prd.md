# refactor llm-worker: убрать лишний код, оставить только чистую нейронку

## Goal

Упростить llm-worker: убрать все fallback-логику, вспомогательные эвристики
и сложность вокруг Qdrant. Оставить только прямой пайплайн
"Kafka in → LLM → Kafka out".

## Что лишнее (выявлено из кода)

### processor.py
- **Строки 29–31** (`_DONE_KEYWORDS`, `_PROGRESS_KEYWORDS`, `_TODO_KEYWORDS`) — используются только в `_pick_column`
- **Строки 45–63** (`format_team_context` → `role_synonyms`) — LLM сам умеет резолвить роли по контексту; синонимы — лишняя логика
- **Строки 76–95** (`_pick_column`) — fallback для column_id, когда LLM не смог; без фолбеков = убрать
- **Строки 163–173** (fallback `_pick_column` в `_extract_tasks`) — вызов `_pick_column` при отсутствии column_id в маппинге

### llm/safe_parser.py
- **Шаги 2–3** (markdown-strip + JSON-block search) — fallback для слабых LLaMA/Mistral. Если модель не умеет — это проблема промпта, не парсера

### models.py
- `TaskExtractionList` и `StatusExtractionList` — fault-tolerant враперы с per-item валидацией и `failed_items`. Если LLM вернул мусор — пусть просто упадёт, не молча отбрасывает

### infra/qdrant.py
- `store_batch` — пишет вектора батчей, никогда не читается обратно
- `is_task_duplicate` / `store_task` — дедупликация, но работает поверх "грязных" данных (хранит задачи до подтверждения, отменённые не удаляет)
- `find_task_by_hint` — резолвинг task_id для статусов, может вернуть удалённый task_id

## Открытые вопросы

(нет)

## Requirements

- Убрать `role_synonyms` из `format_team_context`
- Убрать `_pick_column`, `_DONE_KEYWORDS`, `_PROGRESS_KEYWORDS`, `_TODO_KEYWORDS`
- Убрать fallback в `_extract_tasks` для column_id (если нет маппинга → `null`)
- `SafeJsonOutputParser`: оставить только шаг 1 (`json.loads`) + шаг 2 (markdown strip); убрать шаг 3 (block search)
- **Qdrant: убрать полностью** — удалить `infra/qdrant.py`, все вызовы `store_batch`, `store_task`, `is_task_duplicate`, `find_task_by_hint`; `resolved_task_id` всегда `null`; `init_collections()` убрать из `main.py`

## Out of Scope

- Изменения в Spring/backend
- Изменения в промптах
- Добавление новых фич

## Technical Notes

- Файлы: `processor.py`, `llm/safe_parser.py`, `models.py`, `infra/qdrant.py`
- `store_batch` нигде не читается в коде — кандидат на удаление
- `find_task_by_hint` может резолвить удалённые задачи — текущая архитектура Qdrant "dirty by design"
