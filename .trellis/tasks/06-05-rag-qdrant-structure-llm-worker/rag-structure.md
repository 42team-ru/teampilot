# RAG / Qdrant — структура для LLM Worker

## Зачем

Две задачи:
1. **Дедупликация** — не создавать задачу, если похожая уже есть.
2. **Резолвинг статуса** — при `status_change` LLM даёт `task_hint` ("авторизация") → нужно найти реальный `task_id`.
3. **Контекст в промпт** *(будущее)* — топ-K похожих задач чата вставляются в промпт перед созданием новой.

---

## Коллекции

### `tasks` (основная)

```
collection: "tasks"
vector_size: 384   # paraphrase-multilingual-MiniLM-L12-v2
distance: Cosine
```

**Документ (text для эмбеддинга):**
```
{title}\n{description}
```

**Payload (metadata):**
```json
{
  "task_id":    "uuid-from-llm-worker",
  "title":      "Реализовать endpoint загрузки файлов",
  "team_id":    "uuid-from-postgres",
  "assignee":   "vova_ml",
  "status":     "TODO",
  "created_at": "2026-06-05T10:00:00Z"
}
```

**Фильтр при запросах:** всегда `team_id == <UUID команды>` — задачи разных команд не смешиваем.
`team_id` не хранится: он нестабилен, `team_id` — постоянный UUID из Postgres.

---

### `message_batches` *(опционально, для будущих дайджестов)*

```
collection: "message_batches"
vector_size: 384
distance: Cosine
```

**Документ:** форматированный текст батча (`[10:00] user: text\n...`)

**Payload:**
```json
{
  "batch_id":  "event-uuid",
  "team_id":   "uuid-from-postgres",
  "timestamp": "2026-06-05T10:00:00Z"
}
```

---

## Функции (infra/qdrant.py)

### Запись

```python
def store_task(task_id: str, title: str, description: str, team_id: int) -> None:
    """Вызывается после генерации задачи, перед публикацией в Kafka."""
    client.add(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        documents=[f"{title}\n{description}"],
        ids=[task_id],
        metadata=[{
            "task_id": task_id,
            "title": title,
            "team_id": team_id,
            "status": "TODO",
        }],
    )

def store_batch(batch_id: str, text: str, team_id: int) -> None:
    """Вызывается для каждого батча."""
    client.add(
        collection_name=settings.QDRANT_COLLECTION_BATCHES,
        documents=[text],
        ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, batch_id))],
        metadata=[{"batch_id": batch_id, "team_id": team_id}],
    )
```

### Чтение

```python
def is_task_duplicate(title: str, description: str, team_id: int) -> bool:
    """Дедуп: similarity > DEDUP_THRESHOLD (0.92) в рамках чата."""
    results = client.query(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        query_text=f"{title}\n{description}",
        limit=1,
        score_threshold=settings.DEDUP_THRESHOLD,
        query_filter=Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        ),
    )
    return bool(results)

def find_task_by_hint(task_hint: str, team_id: int) -> str | None:
    """Резолвинг статуса: находит task_id по краткому хинту от LLM."""
    results = client.query(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        query_text=task_hint,
        limit=1,
        score_threshold=0.70,   # порог ниже чем у дедупа — хинт короткий
        query_filter=Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        ),
    )
    return results[0].metadata["task_id"] if results else None

def get_tasks_context(text: str, team_id: int, limit: int = 5) -> list[dict]:
    """RAG-контекст: топ-K похожих задач для инъекции в промпт."""
    results = client.query(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        query_text=text,
        limit=limit,
        query_filter=Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        ),
    )
    return [r.metadata for r in results]
```

---

## Точки интеграции в main.py

```
process_batch(batch)
  │
  ├─ store_batch(...)                    # всегда
  │
  ├─ [has_task] _extract_tasks(...)
  │     ├─ is_task_duplicate(title, desc, team_id)  → skip if True
  │     └─ store_task(task_id, ...)      # только для новых задач
  │
  └─ [has_status_change] _extract_statuses(...)
        └─ find_task_by_hint(hint, team_id)  → добавить task_id в StatusChangeEvent
```

### Будущее: RAG-контекст в промпт

```python
# Перед вызовом task_chain в _extract_tasks:
existing = get_tasks_context(text, batch.team_id, limit=5)
existing_ctx = format_existing_tasks(existing)  # "- Реализовать S3 [TODO, vova_ml]\n..."

raw = task_chain.invoke({
    "messages": text,
    "existing_tasks": existing_ctx,   # новое поле в промпте
    ...
})
```

---

## Инициализация коллекций

```python
# infra/qdrant.py — вызывается один раз при старте

def init_collections() -> None:
    client = get_qdrant_client()
    for name in [settings.QDRANT_COLLECTION_TASKS, settings.QDRANT_COLLECTION_BATCHES]:
        if not client.collection_exists(name):
            client.create_collection(name, ...)
            # FastEmbed сам создаст коллекцию через client.add(),
            # но явный create нужен для задания параметров
```

---

## Пороги

| Сценарий         | Threshold | Почему                                      |
|------------------|-----------|---------------------------------------------|
| Дедуп задач      | 0.92      | Строгий — только явные дубли                |
| Резолвинг хинта  | 0.70      | Мягкий — хинт ("авторизация") короткий      |
| RAG-контекст     | без порога| Топ-K по близости, порог не нужен           |

---

## Что НЕ делаем сейчас (out of scope)

- Обновление вектора при смене статуса задачи (Spring знает о статусах, не LLM worker)
- Удаление из Qdrant при отмене задачи
- Эмбеддинги для аудио-транскриптов отдельно
- Коллекция для "command style" — слишком сложно для MVP
