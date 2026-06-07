# status-chain: task matching via Qdrant (threshold / search quality fix)

## Goal

Исправить `task_id=None` при обработке статусных сообщений. Задача в Qdrant есть,
поиск `search_tasks()` её не возвращает — либо score < threshold, либо запрос
семантически далёк от title задачи.

## Root Cause (confirmed from logs)

```
02:19:54  store_task('af40bd16') ← "Реализовать эндпоинт для поиска..." в Qdrant
02:22:02  search_tasks("Эндпоинт для поиска готов, смотри в PR #47") → [] → task_id=None
```

Задача была в Qdrant за 2 минуты до обработки батча. Timing ни при чём.

Гипотезы:
1. `STATUS_HINT_THRESHOLD = 0.70` слишком высокий — match есть, но score ниже порога
2. Запрос-статус ("Эндпоинт готов, смотри в PR") семантически далёк от title ("Реализовать эндпоинт") для используемого embedding-модели

## Requirements

* Добавить debug-лог в `_search_status_task_candidates` ПЕРЕД фильтрацией по threshold, чтобы видеть реальный score
* Откалибровать `STATUS_HINT_THRESHOLD` на основании реальных score значений
* Если score у правильного кандидата стабильно < 0.70 — снизить порог до рабочего значения

## Acceptance Criteria

* [ ] В логах видны score кандидатов из Qdrant при status-поиске
* [ ] Задача "Реализовать эндпоинт для поиска по базе знаний" появляется в кандидатах при запросе "Эндпоинт для поиска готов, смотри в PR #47"
* [ ] `task_id != None` для статусного сообщения о готовом эндпоинте

## Technical Approach

**Шаг 1 — диагностика (1 файл, ~5 строк):**
В `infra/qdrant.py` → `search_tasks()` или `_query_task_points()`: добавить лог всех candidates
с их score ДО применения threshold. Запустить тест снова, посмотреть на score.

**Шаг 2 — fix (в зависимости от результата):**
- Если score > 0 но < 0.70 → снизить `STATUS_HINT_THRESHOLD` в `settings.py`
- Если score ≈ 0 → проблема embedding качества, нужно другое решение

## Decision (ADR-lite)

**Context**: search_tasks возвращает [] для семантически близкого запроса

**Decision**: Сначала диагностика, потом threshold tuning

**Consequences**: 
- Минимальное изменение — только settings.py + лог
- Если embedding quality poor — возможно нужна смена модели или query rewriting

## Out of Scope

* Spring lifecycle changes (timing не проблема)
* Изменение proto/batch протокола
* Смена embedding модели (только если диагностика покажет 0 score)

## Technical Notes

**Файлы:**
- `llm-worker/infra/qdrant.py` — добавить лог score до threshold
- `llm-worker/settings.py` — `STATUS_HINT_THRESHOLD: float = 0.70` (возможно снизить)

**Ключевой код для диагностики (`search_tasks`):**
```python
def search_tasks(query, team_id, limit=5, score_threshold=None):
    threshold = settings.STATUS_HINT_THRESHOLD if score_threshold is None else score_threshold
    points = _query_task_points(query, team_id, limit=limit, score_threshold=threshold)
    # нужно логировать что вернул _query_task_points до фильтрации
```

**Статус-запросы из теста:**
- query: "Эндпоинт для поиска готов, смотри в PR #47"
- target task title: "Реализовать эндпоинт для поиска по базе знаний"
- task_id: af40bd16-58df-4233-9bf5-942dd6346fb7
