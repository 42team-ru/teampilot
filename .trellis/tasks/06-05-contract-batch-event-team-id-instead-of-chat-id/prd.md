# contract: team_id вместо chat_id в MessageBatchEvent / LlmTaskCreateEvent

## Goal

Заменить `chatId: Long` на `teamId: UUID` во всём контракте между Spring и LLM worker.
`chat_id` может измениться (Telegram группа переедет), `team.id` — стабильный UUID из Postgres.

## Requirements

- `MessageBatchEvent` (Java + Proto): поле `chatId` → `teamId` (string UUID)
- `LlmTaskCreateEvent` (Java): поле `chatId: Long` → `teamId: String` (UUID)
- `ChatMessageBatchPublisher`: передавать `team.getId().toString()` вместо `chatId`
- `ChatMessageBatchingService`: при поиске по БД всё ещё использует `chatId`, но в публикацию кладёт `teamId`
- LLM worker `models.py`: `chat_id: int` → `team_id: str`
- LLM worker `main.py`: Qdrant фильтр `chat_id` → `team_id`
- Proto-файл: добавить `team_id` (string), убрать `chat_id`

## Acceptance Criteria

- [ ] `MessageBatchEvent` не содержит `chatId`
- [ ] `LlmTaskCreateEvent` не содержит `chatId`
- [ ] LLM worker корректно десериализует `team_id` из proto
- [ ] Qdrant queries фильтруют по `team_id`
- [ ] Компиляция monolith чистая, тесты зелёные

## Out of Scope

- Изменение логики батчинга (всё ещё по chatId в БД)
- Обновление `StatusChangeEvent` (отдельный таск если нужно)

## Technical Notes

Файлы:
- `backend/monolith/src/.../event/MessageBatchEvent.java`
- `backend/monolith/src/.../event/LlmTaskCreateEvent.java`
- `backend/monolith/src/.../service/ChatMessageBatchPublisher.java`
- `backend/monolith/src/.../service/ChatMessageBatchingService.java`
- `llm-worker/models.py`
- `llm-worker/main.py`
- `llm-worker/infra/qdrant.py`
- Proto-файл (путь уточнить: `backend/core/kafka-common/src/...`)
