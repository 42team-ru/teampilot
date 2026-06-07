# qdrant-refactor-payload-indexes

## Goal

Привести инициализацию Qdrant в порядок: добавить payload-индексы на `team_id` для быстрой фильтрации, сделать `init_collections()` идемпотентной и поддерживающей все коллекции (tasks + knowledge), убрать мёртвый `QDRANT_COLLECTION_BATCHES`.

Это фундамент для задач knowledge-base-qdrant-core и knowledge-base-bot-qa — они требуют наличия коллекции `knowledge` при старте.

## What I already know

- `infra/qdrant.py` → `init_collections()` создаёт только `tasks`, без payload-индексов
- `settings.py` содержит `QDRANT_COLLECTION_BATCHES = "message_batches"` — нигде не используется (мёртвая конфигурация)
- `main.py` вызывает `init_collections()` при старте — единственный caller
- Qdrant `create_payload_index` идемпотентен: вызов на уже проиндексированном поле — no-op
- Текущий `tasks` collection: каждый поиск делает vector search + full-scan по `team_id` фильтру
- В `_query_task_points` используется `Filter(must=[FieldCondition(key="team_id", ...)])` — именно это поле нужно проиндексировать
- `QDRANT_COLLECTION_TASKS` и `QDRANT_COLLECTION_BATCHES` в settings; нужно добавить `QDRANT_COLLECTION_KNOWLEDGE`

## Requirements

- [ ] `init_collections()` переименовать в `ensure_collections()` (идемпотентная, вызывается при каждом старте)
- [ ] `ensure_collections()` создаёт `tasks` коллекцию если не существует
- [ ] `ensure_collections()` добавляет payload-индекс `team_id` (keyword) на `tasks`
- [ ] `ensure_collections()` создаёт `knowledge` коллекцию если не существует (та же размерность вектора)
- [ ] `ensure_collections()` добавляет payload-индекс `team_id` (keyword) на `knowledge`
- [ ] `ensure_collections()` добавляет payload-индекс `type` (keyword) на `knowledge` (фильтрация по meeting_summary / decision / term / excerpt)
- [ ] `QDRANT_COLLECTION_BATCHES` удалить из settings.py (мёртвая конфигурация)
- [ ] `QDRANT_COLLECTION_KNOWLEDGE` добавить в settings.py (default: `"team_knowledge"`)
- [ ] Обновить импорт в `main.py`: `init_collections` → `ensure_collections`

## Acceptance Criteria

- [ ] После `ensure_collections()` обе коллекции (`tasks`, `knowledge`) существуют в Qdrant
- [ ] Повторный вызов `ensure_collections()` не бросает исключений (идемпотентность)
- [ ] `create_payload_index` вызывается для `team_id` в обеих коллекциях
- [ ] `QDRANT_COLLECTION_BATCHES` отсутствует в `settings.py`
- [ ] `main.py` вызывает `ensure_collections()` без ошибки

## Definition of Done

- Код в `infra/qdrant.py` и `settings.py` обновлён
- `main.py` обновлён (импорт переименован)
- Нет сломанных импортов в других файлах

## Technical Approach

В `infra/qdrant.py`:
```python
from qdrant_client.models import PayloadSchemaType

def ensure_collections() -> None:
    client = get_qdrant_client()
    for name in [settings.QDRANT_COLLECTION_TASKS, settings.QDRANT_COLLECTION_KNOWLEDGE]:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=settings.EMBEDDINGS_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {name}")
        client.create_payload_index(
            collection_name=name,
            field_name="team_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
```

## Out of Scope

- Изменение логики `store_task`, `search_tasks`, `is_task_duplicate`
- Добавление данных в `knowledge` коллекцию (это задача knowledge-base-qdrant-core)
- Другие payload-индексы (kind, type и т.д.) — добавить при необходимости в следующих задачах

## Technical Notes

- `infra/qdrant.py` — файл изменений
- `settings.py` — добавить QDRANT_COLLECTION_KNOWLEDGE, удалить QDRANT_COLLECTION_BATCHES
- `main.py:10` — строка с `from infra.qdrant import delete_task, init_collections, store_task`
- Qdrant `create_payload_index` для уже существующего индекса: возвращает 200 OK, не падает
