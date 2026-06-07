# Meeting real-time hints: "такая задача уже есть"

## Goal

Во время звонка, когда LLM находит потенциальную задачу в транскрипте чанка, проверить через Qdrant есть ли уже похожая задача в команде. Если есть — сформировать hint-строку и передать её фронтенду через существующий WebSocket-поток (MeetingLiveResultEvent → Spring → WebSocket).

## Requirements

### Python (llm-worker)

* Добавить `hints: list[str] = []` в `MeetingLiveResultEvent` (models.py)
* В `process_meeting_audio` (processor.py) — после вызова `_process_transcript_chunk` и получения `extracted_events`:
  - Для каждого `TaskCreateEvent` в `extracted_events` вызвать `search_tasks(title, team_id, limit=1)` с низким порогом (использовать `settings.DEDUP_THRESHOLD` или 0.80)
  - Если найден хит — добавить в `hints` строку вида: `"Похожая задача уже есть: «{matched_title}»"`
  - Это делать и для chunk-level событий, и для событий из полного транскрипта (финализация)
* Передавать `hints` в `MeetingLiveResultEvent` при publish

### Java (Spring monolith)

* `MeetingLiveResultEvent.java` — добавить поле `List<String> hints` с `@Builder.Default = List.of()`
* `MeetingLiveResultResponse.java` — добавить `List<String> hints` в record и в `from()` маппер
* `MeetingLiveResultConsumer.java` — изменений не нужно (маппер `from()` подхватит автоматически)

## Acceptance Criteria

* [ ] `MeetingLiveResultEvent` (Python) содержит `hints: list[str]`
* [ ] При нахождении похожей задачи в Qdrant — hints непустой
* [ ] `MeetingLiveResultEvent.java` содержит `List<String> hints`
* [ ] `MeetingLiveResultResponse.java` содержит `List<String> hints` и маппер их передаёт
* [ ] WebSocket-пуш содержит поле `hints` (автоматически через маппер)

## Out of Scope

* UI в расширении (отдельно)
* Блокировка создания задачи при наличии хинта (хинт только информационный)
* Отдельный Kafka-топик для хинтов

## Technical Notes

### Python
* `models.py:213` — `MeetingLiveResultEvent`
* `processor.py:946` — `process_meeting_audio`; hint-проверка после строк 981–993 (chunk events) и после строки 1021 (full transcript events)
* `infra/qdrant.py:296` — `search_tasks(query, team_id, limit, score_threshold)` — уже импортирован в processor.py строка 14
* Порог для хинта: использовать `settings.DEDUP_THRESHOLD` или явное значение 0.80
* Hint формируется только если `team_id` не None

### Java
* `MeetingLiveResultEvent.java` — добавить по образцу существующих `@Builder.Default` полей `tasks`/`statuses`
* `MeetingLiveResultResponse.java` — record field + маппинг из event
* Используем `@JsonIgnoreProperties(ignoreUnknown = true)` — уже стоит, Python может слать дополнительные поля без сломанного десериализатора
