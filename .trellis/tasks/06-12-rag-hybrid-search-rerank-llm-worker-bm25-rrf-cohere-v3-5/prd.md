# RAG hybrid search + rerank в llm-worker

## Goal

Переделать RAG в `llm-worker` с чистого dense-поиска на современный двухстадийный пайплайн:
**hybrid (OpenAI dense + локальный BM25 sparse) → RRF-fusion в Qdrant → Cohere Rerank v3.5 (через OpenRouter)**.
Цель — поднять точность поиска задач/knowledge (особенно по именам, тикетам, точным терминам на русском),
убрать костыли (4 представления на задачу, `match_boost`, магический порог 0.25) и уложиться в 4 ГБ RAM VDS.

## What I already know

- Текущий код: `infra/qdrant.py` — dense-only, 4 точки-представления на задачу, ручная агрегация + `match_boost`.
- `qdrant-client==1.18.0` (есть `FusionQuery`), `fastembed==0.8.0` (есть `SparseTextEmbedding("Qdrant/bm25")`) — уже установлены.
- OpenRouter уже в стеке (TTS) → реранк-ключ переиспользуем.
- Потребители RAG (сигнатуры менять нельзя): `processor.py`, `sync_processor.py`, `meeting_processor.py`, `voice_agent.py`, `api.py`, `main.py`.
- Детали API/синтаксиса — в [`research/rag-hybrid-rerank.md`](research/rag-hybrid-rerank.md).

## Requirements

- Коллекции `tasks` и `team_knowledge` пересоздать с именованными векторами: `dense` (1536, cosine) + sparse `bm25`.
- `store_task` / `store_knowledge` пишут **одну** точку с обоими векторами (dense + bm25). Убрать схему из 4 представлений и `status`-вектор.
- Поиск (`_query_task_points`, `search_knowledge`) → `query_points` с `prefetch[dense, bm25]` + `FusionQuery(RRF)`, `limit≈20`.
- Новый модуль реранка: вызов `POST https://openrouter.ai/api/v1/rerank`, модель `cohere/rerank-v3.5`, top_n=limit.
- Реранк применяется в `search_tasks` и `search_knowledge` (→ затрагивает processor status-поиск, sync, meeting, api).
- **voice_agent — без реранка** (латентность живого звонка): отдельный путь / флаг `rerank=False`.
- Публичные сигнатуры `search_tasks` / `search_knowledge` / `store_task` / `store_knowledge` / `is_task_duplicate` / `delete_*` — без изменений (потребители не трогаем).
- Грейсфул-деградация: если rerank API недоступен/упал → возвращаем RRF-порядок (не падаем). Эмбеддинг/Qdrant ошибки — как сейчас (try/except → []).
- Новые настройки в `settings.py` + `.env.example`: `RERANK_API_BASE`, `RERANK_API_KEY`, `RERANK_MODEL`, `RERANK_TOP_N`, `RERANK_CANDIDATES` (=20), `RERANK_ENABLED`.

## Acceptance Criteria

- [ ] Коллекции создаются с dense+bm25; `ensure_collections()` идемпотентен.
- [ ] `store_task`/`store_knowledge` пишут 1 точку с двумя векторами; старые 4-представления больше не создаются.
- [ ] `search_tasks`/`search_knowledge` возвращают результаты через hybrid+RRF, затем rerank top-N.
- [ ] При `RERANK_ENABLED=false` или ошибке rerank API — корректный фолбэк на RRF-порядок.
- [ ] `voice_agent` поиск работает без вызова rerank.
- [ ] Дедуп (`is_task_duplicate`) и sync-матчинг продолжают работать (пороги перекалиброваны под новый scoring).
- [ ] `scripts/check_qdrant.py` обновлён под новую схему / не падает.
- [ ] Прогон на `make core-up` + реальном батче: поиск возвращает осмысленные результаты (ручная проверка).

## Definition of Done

- Код проходит существующие проверки воркера, ручной прогон поиска зелёный.
- `.env.example` обновлён, новые настройки задокументированы.
- Старые костыли (`_task_representations` status-вектор, `match_boost`, порог 0.25) удалены или явно вынесены из пути.
- Поведение потребителей не сломано (сигнатуры стабильны).

## Out of Scope (MVP)

- Чанкинг knowledge / contextual retrieval (Anthropic) — Tier 2, отдельная задача.
- Переход на локальные эмбеддинги (e5/bge-m3) — остаёмся на OpenAI dense.
- Eval-харнесс (MRR/NDCG) и автокалибровка порогов — отдельная задача.
- Реранк в voice-агенте.
- MMR-диверсификация, квантизация/тюнинг HNSW.

## Decision (ADR-lite)

**Context**: Переход на hybrid-схему несовместим со старыми коллекциями; нужно решить миграцию, область реранка и объём MVP.
**Decision**:
- **Миграция**: пересоздать коллекции с нуля (drop + create dense+bm25). Данные перельются из lifecycle-событий / по мере работы. Старый knowledge до переиндексации теряется — приемлемо для хакатона.
- **Дедуп**: `is_task_duplicate` остаётся на hybrid+threshold, БЕЗ rerank (бинарное решение, экономим вызовы и latency).
- **Scope**: только hybrid + RRF + rerank. Чанкинг knowledge, eval-харнесс, локальные эмбеддинги — отдельные задачи.
**Consequences**: Минимум работы до рабочего результата; теряем исторический knowledge при первом запуске; пороги дедупа/синка надо перекалибровать под RRF-скор.

## Research References

- [`research/rag-hybrid-rerank.md`](research/rag-hybrid-rerank.md) — синтаксис Qdrant hybrid, fastembed BM25, OpenRouter rerank API, цены, точки вызова.

## Technical Notes

- Реранк-эндпоинт: `POST https://openrouter.ai/api/v1/rerank`, body `{model, query, documents, top_n}`, resp `{results:[{index, relevance_score}]}`.
- BM25: `SparseTextEmbedding("Qdrant/bm25")`, `passage_embed` для индексации, `query_embed` для запроса.
- Пороги (`STATUS_HINT_THRESHOLD`, `DEDUP_THRESHOLD`, `SYNC_MATCH_THRESHOLD`) завязаны на старую dense-шкалу → после rerank scoring другой (relevance_score 0..1), нужна перекалибровка.
