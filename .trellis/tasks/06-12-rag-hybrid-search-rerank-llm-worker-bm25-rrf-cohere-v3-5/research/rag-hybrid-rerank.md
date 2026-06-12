# Research: Hybrid search (BM25 + dense) + RRF + Cohere rerank

## Текущее состояние (`llm-worker/infra/qdrant.py`)
- Только dense, OpenAI `text-embedding-3-small` (1536d), cosine, дефолтный HNSW.
- На каждую задачу пишется **4 точки-представления** (`summary/title/description/status`), потом ручная агрегация по `task_id` + `match_boost` (костыль вместо fusion).
- `status`-представление = склейка 20 глаголов × title → семантически грязный вектор, ломает дедуп.
- Knowledge — без чанкинга, одна точка на документ.
- Порог `STATUS_HINT_THRESHOLD=0.25` тянет почти-шум.
- Нет lexical-поиска и нет реранкера.

## Установлено в окружении
- `qdrant-client==1.18.0` — есть и `FusionQuery`, и `RrfQuery`.
- `fastembed==0.8.0` — даёт `SparseTextEmbedding("Qdrant/bm25")` (статистический BM25, ~0 RAM/CPU, $0).
- OpenRouter уже в стеке (TTS): `TTS_API_BASE=https://openrouter.ai/api/v1`.

## Ограничения железа
- VDS: 4 ГБ RAM, 2 vCPU. Локальные нейро-реранкеры (bge-reranker-v2-m3 ~2 ГБ) НЕ влезают.
- Решение: dense через OpenAI API (0 RAM локально), sparse через локальный BM25 (~50 МБ), rerank через API (0 RAM).

## Qdrant hybrid (Query API, проверено под 1.18)
Коллекция с именованными векторами:
```python
client.create_collection(
    collection_name="tasks",
    vectors_config={"dense": models.VectorParams(size=1536, distance=models.Distance.COSINE)},
    sparse_vectors_config={"bm25": models.SparseVectorParams()},
)
```
Upsert точки с обоими векторами:
```python
models.PointStruct(id=..., vector={"dense": [...], "bm25": models.SparseVector(indices=[...], values=[...])}, payload={...})
```
Hybrid-поиск с RRF:
```python
client.query_points(
    collection_name="tasks",
    prefetch=[
        models.Prefetch(query=dense_vec, using="dense", limit=20, filter=flt),
        models.Prefetch(query=models.SparseVector(...), using="bm25", limit=20, filter=flt),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=20,
)
```
RRF сливает по рангам (не по сырым баллам — у dense/BM25 разные шкалы).

## fastembed BM25
```python
from fastembed import SparseTextEmbedding
bm25 = SparseTextEmbedding("Qdrant/bm25")  # есть параметр language="russian" для стоп-слов/стемминга
emb = next(bm25.passage_embed([text]))     # .indices, .values
qemb = next(bm25.query_embed(query))
```
Для индексации — `passage_embed`, для запроса — `query_embed` (учитывает IDF корпуса).

## OpenRouter rerank API
- Endpoint: `POST https://openrouter.ai/api/v1/rerank`
- Auth: `Authorization: Bearer <OPENROUTER_API_KEY>`
- Body: `{ "model": "cohere/rerank-v3.5", "query": "...", "documents": ["...","..."], "top_n": 5 }`
- Response: `{ "results": [ { "index": <int>, "relevance_score": <float> }, ... ] }`
- Модель: **`cohere/rerank-v3.5`** — $0.001/search, 4K контекст, 100+ языков (русский ок).
  - Альтернативы: `cohere/rerank-4-fast` ($0.002, 32K), `cohere/rerank-4-pro` ($0.0025, 32K). Pro = ДОРОЖЕ.

## Цена реранка для проекта
- ~150–300 вызовов/день на активную команду → $0.15–0.30/день. За хакатон < $1–2.
- Точки вызова (1 search_* = 1 rerank): `processor._extract_tasks` (knowledge + dedup per task),
  `processor._search_status_task_candidates` (до 6 запросов), `sync_processor` (per line),
  `meeting_processor` (per task), `api.py` (manual). **voice_agent — БЕЗ реранка (латентность).**

## Best practices (из ресёрча)
- Hybrid (dense+sparse+RRF) стабильно бьёт одиночные ретриверы.
- Two-stage: retrieve ~20 (recall) → rerank top-5 (precision). Реранкер — самый влиятельный компонент (+17 п.п. MRR, +12 п.п. recall@5).
- Чанкинг knowledge + contextual retrieval (Anthropic) — Tier 2, в этот MVP не входит.

## Источники
- https://qdrant.tech/documentation/search/hybrid-queries/
- https://qdrant.tech/articles/hybrid-search/
- https://openrouter.ai/docs/api/api-reference/rerank/create-rerank
- https://openrouter.ai/cohere/rerank-v3.5
- https://towardsdatascience.com/hybrid-search-and-re-ranking-in-production-rag/
