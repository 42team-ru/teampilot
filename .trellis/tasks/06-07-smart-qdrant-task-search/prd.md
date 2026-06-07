# Умный поиск задач в Qdrant

## Goal

Improve LLM Worker task retrieval so status-change extraction and duplicate detection do not depend on a single embedding of the whole task. The worker should retrieve better task candidates from short, noisy chat phrases like "закрыл авторизацию" or "qdrant готов" while keeping the existing Spring -> Python `tasks.lifecycle` contract.

## What I already know

* Current `llm-worker/infra/qdrant.py` stores one vector per task from `title + description`.
* Current `search_tasks(query, team_id)` embeds the whole message batch/chunk and returns top 5 by `team_id`.
* Status prompts receive only `task_id` and `title`, so the model cannot use description or score when choosing a task.
* `tasks.lifecycle` currently carries only `taskId`, `teamId`, `type`, `title`, `description`.
* `tasks.lifecycle` is consumed only for Qdrant sync in LLM Worker; cancelled tasks must be removed from the index.

## Assumptions

* Do not change the Spring Kafka contract in this task.
* Keep the existing public Python call shape where possible: `store_task`, `delete_task`, `search_tasks`, `is_task_duplicate`.
* Avoid new external dependencies.
* Keep Qdrant collection name and vector config unchanged so existing deployments can continue using the same collection.

## Requirements

* Store multiple searchable representations per task instead of one "whole task" vector.
* Preserve task-level filtering by `team_id`.
* Aggregate multiple Qdrant hits back into one candidate per task.
* Build focused status-search queries from status-like messages instead of
  embedding the entire noisy message batch.
* Return richer candidates to the status prompt: title, description snippet, matched representation, score.
* Make duplicate detection use the improved search/indexing path.
* Delete all Qdrant points for a cancelled task.
* Keep failures non-fatal: Qdrant/embedding errors should log warnings and return safe defaults.

## Acceptance Criteria

* [ ] `store_task` upserts multiple Qdrant points per task with stable point IDs.
* [ ] `delete_task` removes every point for a task, not only one point ID.
* [ ] `search_tasks` searches across task representations and returns unique task candidates.
* [ ] Status extraction searches Qdrant with focused message/snippet queries, not only the full batch text.
* [ ] `format_task_candidates` includes enough context for LLM status selection.
* [ ] `is_task_duplicate` still works and benefits from richer indexed text.
* [ ] Unit tests cover aggregation, candidate formatting, and deletion selector behavior without requiring a live Qdrant service.

## Definition of Done

* Tests added/updated for changed behavior.
* Relevant `llm-worker` tests pass.
* Backend Kafka contract is not changed unless explicitly required.
* Any newly learned Qdrant lifecycle convention is captured in `.trellis/spec/` if it becomes a project rule.

## Out of Scope

* Full hybrid BM25 + vector search.
* Backend lifecycle event expansion with assignee/deadline/status fields.
* Reindex migration job for old single-point tasks.
* LLM-based pre-extraction of status search queries before Qdrant lookup.
* Changing embedding provider/model.

## Technical Notes

* Relevant files:
  * `llm-worker/infra/qdrant.py`
  * `llm-worker/processor.py`
  * `llm-worker/models.py`
  * `.trellis/spec/backend/kafka-events.md`
* Current lifecycle Java producer: `backend/monolith/src/main/java/ru/team42/monolith/event/TaskLifecycleEvent.java`.
* Existing Qdrant settings: `QDRANT_COLLECTION_TASKS`, `DEDUP_THRESHOLD`, `STATUS_HINT_THRESHOLD`.
* Candidate retrieval should stay defensive because status-change extraction can proceed with `task_id = null` if Qdrant has no match.
