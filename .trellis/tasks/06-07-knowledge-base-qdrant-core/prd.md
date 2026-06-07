# knowledge-base-qdrant-core

## Goal

Реализовать хранение и поиск знаний команды в Qdrant-коллекции `team_knowledge`.
Знания накапливаются автоматически из митингов и задач, и используются как контекст в LLM-промптах для более точного извлечения задач.

## What I already know

- `team_knowledge` коллекция уже создана task 1 (`ensure_collections`) с индексами `team_id` и `type`
- `settings.QDRANT_COLLECTION_KNOWLEDGE = "team_knowledge"` добавлен
- `generate_file_summary` публикует `FileSummaryEvent` в Kafka И возвращает `summary` — можно сразу записывать в knowledge
- `process_meeting_audio(final_chunk=True)` → `_finalize_meeting_recording` → возвращает `MeetingFinalizationResult` с `.summary`, `.title`, `.full_transcript`
- `TaskLifecycleEvent` CONFIRMED/UPDATED → уже вызывает `store_task` в `tasks` коллекции → добавить `store_knowledge` как `task_archive`
- `llm/chains.py` — 6 цепочек: classifier, task, status, audio_task, audio_status, file_summary
- `llm/prompts.py` — 853 строки, уже содержит секцию TASK CANDIDATES (для поиска задач); нужно добавить `{knowledge_context}`
- `processor.py:_extract_tasks` — место для inject knowledge context перед вызовом `task_chain`

## Types of knowledge

| type | Источник | Когда записывать |
|------|----------|-----------------|
| `meeting_summary` | `_finalize_meeting_recording` | `final_chunk=True` |
| `file_summary` | `generate_file_summary` | после генерации summary |
| `task_archive` | `TaskLifecycleEvent` CONFIRMED/UPDATED | в lifecycle consumer |

## Requirements

- [ ] `infra/qdrant.py` → `store_knowledge(source_id, team_id, type, content, title?)` — upsert в `team_knowledge`
- [ ] `infra/qdrant.py` → `search_knowledge(query, team_id, type?, limit)` → `list[dict]`
- [ ] `infra/qdrant.py` → `delete_knowledge(source_id)` — удаление при отмене
- [ ] Ingestion: meeting finalization → `store_knowledge(type="meeting_summary")`
- [ ] Ingestion: file summary → `store_knowledge(type="file_summary")`
- [ ] Ingestion: lifecycle CONFIRMED/UPDATED → `store_knowledge(type="task_archive")`
- [ ] `processor.py:_extract_tasks` → `search_knowledge(text, team_id)` → `knowledge_context` → передаётся в `task_chain`
- [ ] `llm/prompts.py` → task prompt принимает `{knowledge_context}` (опциональный раздел)

## Decision (ADR-lite)

**Context**: нужен гейтинг `decision_chain` чтобы не тратить LLM на каждый батч
**Decision**: Вариант A — через классификатор: добавить `has_decision` + `confidence_decision` в `ClassificationResult` и classifier prompt. Симметрично `has_task` / `has_status_change`.
**Consequences**: нужно изменить рабочую схему `ClassificationResult` и classifier промпт. Зато единственная точка гейтинга для всех извлечений.

## Acceptance Criteria

- [ ] После финализации митинга в `team_knowledge` появляется точка с `type=meeting_summary`
- [ ] После CONFIRMED задачи в `team_knowledge` появляется точка с `type=task_archive`
- [ ] `_extract_tasks` получает knowledge_context (не падает если knowledge пусто)
- [ ] task prompt в prompts.py содержит блок KNOWLEDGE CONTEXT
- [ ] `delete_knowledge` удаляет точку при CANCELLED задаче

## Definition of Done

- Все Acceptance Criteria выполнены
- Нет broken imports
- Логирование: store/search/delete knowledge пишут в logger

## Out of Scope
- Q&A хендлер в боте (задача 3)
- Dedup через knowledge (не меняем `is_task_duplicate`)
- status_chain, audio_status_chain — не получают knowledge_context в MVP

## Technical Notes

- `source_id` используется как детерминированный UUID (namespace + source_id) — как у `_task_point_id`
- Один вектор на knowledge-точку (нет multi-vector как у tasks) — knowledge ищется по смыслу, не нужна специализация
- `search_knowledge` вернёт `[]` если Qdrant упал — не блокирует основной flow
- `task_chain.invoke` в `_extract_tasks` уже принимает dict — добавить ключ `knowledge_context`
