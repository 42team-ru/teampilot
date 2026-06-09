# Add fallback for status query extraction

## Goal

`status_query_chain` (cheap LLM) возвращает `[]` для коротких/неочевидных сообщений ("испек булки"). Qdrant не получает кандидатов → `statuses=0`. Нужен fallback: когда LLM не извлёк запросы, использовать тексты всех сообщений батча напрямую.

## Requirements

* Если `status_query_chain` вернул `[]` → fallback на `[message.text for message in batch.messages]` как список Qdrant-запросов
* Fallback логируется на уровне DEBUG
* Нет изменений в цепочке — только в `_status_queries_via_llm` / `_status_queries_from_batch`

## Acceptance Criteria

* [ ] Батч `["испек булки", "фронтенд мусорная задача"]` → Qdrant получает хотя бы один запрос
* [ ] Батч с явными задачами ("разработал бекенд") → LLM извлекает нормализованный запрос, fallback не нужен
* [ ] Нет регрессий в task extraction

## Out of Scope

* Изменение STATUS_QUERY_SYSTEM промпта
* Изменение порогов
