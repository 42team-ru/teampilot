# Generic Sticker Support (YouGile Sync + LLM)

## Goal

Синкать все стикеры команды из YouGile в БД (по аналогии с колонками). При батчинге передавать их LLM-у. LLM сам решает какие стикеры и состояния выставить на каждую задачу. Результат хранится в `Task.stickers` (jsonb) и синкается в YouGile при создании/обновлении.

## Flow

```
YouGileBoardSyncService.syncTeam(team)
  → syncStickers(team)  ← новый метод, рядом с syncColumns
    → YouGile API: sprint + string stickers by boardId
    → upsert YouGileSticker / YouGileStickerState в БД

ChatMessageBatchingService.flushBatches()
  → загружает stickers из БД (by team)
  → включает StickerDef в proto MessageBatchEvent

LLM Worker
  → парсит StickerDef из батча
  → extractor-промпт: "выбери stateId для каждого стикера если применимо"
  → output: [{title, description, assignee, deadline, column_id, stickers: {stickerId: stateId}}]

LlmTaskCreateEvent
  → stickers: Map<String, String>

TaskService.createFromLlmEvent
  → task.setStickers(event.getStickers())

YouGileService.createTask / updateTask
  → dto.setStickers(task.getStickers())
```

## Requirements

### БД
* [ ] Entity `YouGileSticker`: id (UUID), team, yougileStickerId, title, type (SPRINT/STRING)
* [ ] Entity `YouGileStickerState`: id (UUID), sticker (ManyToOne), yougileStateId, title
* [ ] `Task.stickers` — `@Type(JsonType) Map<String,String>` (nullable, jsonb)

### Spring sync
* [ ] `YouGileService.fetchStickers(team)` — вызывает `sprintStickerControllerSearch` + `stringStickerControllerSearch` по `boardId`
* [ ] `YouGileBoardSyncService.syncStickers(team)` — upsert YouGileSticker + YouGileStickerState (паттерн syncColumns)
* [ ] `syncTeam(team)` вызывает `self.syncStickers(team)` перед обработкой тасков

### Proto / Batch
* [ ] `message_batch.proto` — добавить `StickerDef { string id=1; string title=2; repeated StickerStateDef states=3; }` и `StickerStateDef { string id=1; string title=2; }` и `repeated StickerDef stickers = 9` в `MessageBatchEvent`
* [ ] `ChatMessageBatchingService` — загружает `YouGileSticker` с `states` из БД, передаёт в `publishBatch`
* [ ] `ChatMessageBatchPublisher.publishBatch` — маппит стикеры в proto

### LLM Worker
* [ ] Парсить `stickers` из proto-батча в `processor.py`
* [ ] Добавить в extractor-промпт секцию STICKER LIST с примером как их выставлять
* [ ] Extractor output: добавить поле `stickers: {stickerId: stateId}` (nullable)
* [ ] `LlmTaskCreateEvent` (Python pydantic/dataclass) — добавить `stickers: dict[str, str] | None`

### Spring create/update
* [ ] `LlmTaskCreateEvent.java` — добавить `stickers: Map<String, String>`
* [ ] `TaskService.createFromLlmEvent` — `task.setStickers(event.getStickers())`
* [ ] `YouGileService.createTask / updateTask` — `dto.setStickers(task.getStickers())`

## Acceptance Criteria

* [ ] После `syncTeam` — `YouGileSticker` + `YouGileStickerState` записаны в БД для команды
* [ ] Батч содержит `stickers` в proto (видно в логах LLM worker)
* [ ] Сообщение "приоритет высокий" → LLM ставит Приоритет=critical → `task.stickers = {"uuid-sticker": "uuid-state"}`
* [ ] Task без явного приоритета → `stickers = null`
* [ ] Стикеры уходят в YouGile при создании задачи

## Out of Scope

* Синк стикеров из YouGile обратно в Task (только outbound)
* UI для управления стикерами
* Числовые/free-text stickers (только sprint stickers для MVP, string stickers — опционально)

## Technical Notes

### Файлы
* `TaskColumn.java` — эталон для YouGileSticker entity
* `YouGileBoardSyncService.syncColumns` — эталон для syncStickers
* `YouGileService.fetchColumns` — эталон для fetchStickers
* `message_batch.proto` — добавить StickerDef (field 9)
* `ChatMessageBatchPublisher.java` — добавить stickers в publishBatch
* `ChatMessageBatchingService.java` — загружать stickers из репозитория
* `llm-worker/llm/prompts.py` — extractor prompt
* `llm-worker/processor.py` — парсить stickers из батча
* `LlmTaskCreateEvent.java` + Python event — добавить stickers

### YouGile API
* `sprintStickerControllerSearch(null, null, null, null, boardId)` → `SprintStickerWithStatesListDto`
* `stringStickerControllerSearch(null, null, null, null, boardId)` → `StringStickerWithStatesListDto`
* `SprintStickerWithStatesDto` — id, name, states[]
* `SprintStickerStateDto` — id, name, begin, end
* `CreateTaskDto.stickers` — `Object` (JSON map `{stickerId: stateId}`)

### JsonType
* Проект уже использует `hypersistence-utils` для jsonb (TaskColumn/Task использует @Type если нужен — проверить)
