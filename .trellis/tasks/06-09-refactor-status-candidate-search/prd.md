# Refactor status candidate search

## Goal

Заменить хрупкую маркерную фильтрацию сообщений (список ключевых слов `_STATUS_SEARCH_MARKERS`)
на семантический поиск кандидатов по всем сообщениям батча — когда классификатор уже сказал
`has_status_change=True`. Это устраняет корневую причину `task_id=None` при использовании
глаголов не из списка.

## What I already know

* `_STATUS_SEARCH_MARKERS` — кортеж из ~50 глаголов/фраз; фильтрует сообщения перед Qdrant-поиском
* `_looks_like_status_query(text)` — True если в тексте есть хоть один маркер
* `_status_queries_from_batch(batch)` — берёт `.text` каждого `message` где `_looks_like_status_query` = True
* `_search_status_task_candidates(team_id, queries)` — для каждого query делает `search_tasks()` (Qdrant)
* `search_tasks()` использует `STATUS_HINT_THRESHOLD=0.25` — семантический порог достаточный
* Классификатор работает на LLM (дешёвая модель) — он уже точно знает что есть статусное событие
* Когда `queries=[]` → `_search_status_task_candidates` возвращает `[]` → LLM видит "TASK CANDIDATES: (none)" → `task_id=null`
* `_clean_status_search_query` — чистит metadata-префиксы вида `[ID: ...] [10:00] username:` и обрезает текст

## Assumptions (temporary)

* Батч обычно 1–5 сообщений, поэтому N Qdrant-запросов вместо ≤N — negligible overhead
* `_STATUS_SEARCH_MARKERS` всё ещё полезны для `_clean_status_search_query` (выравнивает окно обрезки вокруг маркера) — но не как жёсткий фильтр

## Open Questions

*(нет)*

## Decision (ADR-lite)

**Context**: Маркерная фильтрация пропускала глаголы не из списка → `task_id=None`
**Decision**: Подход A — один LLM-вызов (cheap model) на весь батч. Модель видит все сообщения, извлекает список упомянутых задач в форме инфинитива → список идёт в Qdrant как поисковые запросы.
**Consequences**: +1 LLM-вызов на батч (~200мс). Устраняет зависимость от словаря маркеров. Полный контекст батча помогает разрешить "взял/делаю" без явного названия задачи.

## Requirements (evolving)

* При `has_status_change=True` все сообщения батча используются как поисковые запросы (не только маркерные)
* `_STATUS_SEARCH_MARKERS` не используются как жёсткий фильтр — `_looks_like_status_query` удаляется
* `_STATUS_SEARCH_MARKERS` и `_status_marker_index` остаются только для умной обрезки в `_clean_status_search_query`
* Qdrant-поиск и `STATUS_HINT_THRESHOLD=0.25` остаются без изменений
* `_clean_status_search_query` сохраняется (чистит metadata-префиксы)

## Acceptance Criteria

* [ ] Сообщение "Я разработал бекенд" при наличии задачи "Разработать бекенд проекта" → `task_id != None`
* [ ] Сообщение "Я настроил бота" → `task_id != None`
* [ ] Сообщение без задачи в Qdrant → `task_id=None` (поведение не ломается)
* [ ] Если `has_status_change=False` — `_extract_statuses` не вызывается (без изменений)

## Definition of Done

* Рефакторинг покрыт юнит-тестом или легко проверяется скриптом `check_qdrant.py`
* Нет регрессий в `_extract_tasks` и `_extract_decisions`

## Out of Scope

* Изменение STATUS_HINT_THRESHOLD
* Изменение status_chain промпта
* Изменение классификатора

## Technical Notes

* Файлы: `llm-worker/processor.py` — функции `_status_queries_from_batch`, `_search_status_task_candidates`, `_extract_statuses`
* `_clean_status_search_query` нужно сохранить — убирает `[ID:...][10:00] username:` из форматированного текста
* `search_tasks()` уже делает `_normalize_text` внутри `_query_task_points` — двойная нормализация не нужна
