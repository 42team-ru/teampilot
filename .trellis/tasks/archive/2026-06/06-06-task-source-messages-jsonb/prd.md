# task-source-messages: ChatMessage → Team + Task.sourceMessages

## Goal

1. Переписать `ChatMessage`: заменить `chatId: Long` на `@ManyToOne Team team`.
2. Добавить `message_id` (UUID) в protobuf `MessageDto`, чтобы LLM-воркер мог ссылаться на конкретные сообщения.
3. Добавить в `Task` поле `sourceMessages: @ManyToMany ChatMessage` — список сообщений, которые стали триггером задачи.
4. Прокинуть `sourceMessageIds: List<UUID>` через `LlmTaskCreateEvent` → `TaskService.createFromLlmEvent`.

## Requirements

* `ChatMessage.chatId: Long` → `ChatMessage.team: @ManyToOne(optional=true) Team` (nullable — если команда не найдена при сохранении)
* `ChatMessageRepository` — переписать запросы: вместо `chatId` использовать `team.id`
* `ChatMessageBatchingService` — искать команды с необработанными сообщениями через `team`
* `ChatMessageService.save()` — резолвить `Team` через `teamRepository.findByTelegramChatId(event.chatId)`; если не найдено — **дропать сообщение** (warn-лог, без сохранения)
* `ChatMessageMapper` — убрать `chatId`, добавить `team` (передаётся из сервиса)
* `message_batch.proto MessageDto` — добавить поле `string message_id = 6` (UUID строкой)
* `ChatMessageBatchPublisher.toProtoMessage()` — заполнять `messageId = m.getId().toString()`
* `LlmTaskCreateEvent` — добавить `List<UUID> sourceMessageIds` (nullable, @JsonIgnoreProperties)
* `Task` — добавить `@ManyToMany @JoinTable(name="task_source_messages") List<ChatMessage> sourceMessages`
* `TaskService.createFromLlmEvent()` — загружать `chatMessageRepository.findAllById(ids)` и устанавливать `task.setSourceMessages(...)`

## Acceptance Criteria

* [ ] `ChatMessage` больше не имеет поля `chatId`; вместо него — `team` (not-null, сообщения без команды не сохраняются)
* [ ] `ChatMessageBatchingService` работает через `team`, без `chatId` в запросах
* [ ] Protobuf `MessageDto` содержит `message_id`
* [ ] `LlmTaskCreateEvent` содержит `sourceMessageIds`
* [ ] При создании Task из события список сообщений сохраняется в join-таблице `task_source_messages`
* [ ] Компилируется; существующие тесты зелёные

## Definition of Done

* Компилируется без ошибок
* Зелёные тесты

## Out of Scope

* REST API для возврата sourceMessages
* Хранение сообщений в Qdrant
* Изменения на стороне LLM-воркера (Python) — только контракт Spring-стороны

## Technical Approach

```
ChatMessage
  - team: @ManyToOne Team (nullable)     ← вместо chatId: Long

Task
  - sourceMessages: @ManyToMany ChatMessage
    @JoinTable(name="task_source_messages",
               joinColumns=@JoinColumn(name="task_id"),
               inverseJoinColumns=@JoinColumn(name="message_id"))

LlmTaskCreateEvent
  + sourceMessageIds: List<UUID>          ← новое поле

MessageDto (proto)
  + message_id: string (field 6)         ← UUID строкой
```

**Порядок изменений:**
1. Protobuf: добавить `message_id`
2. `ChatMessage`: заменить `chatId` → `team`
3. `ChatMessageMapper`, `ChatMessageService`, `ChatMessageRepository`, `ChatMessageBatchingService`
4. `ChatMessageBatchPublisher`: заполнять `message_id`
5. `LlmTaskCreateEvent`: добавить `sourceMessageIds`
6. `Task`: добавить `@ManyToMany sourceMessages`
7. `TaskService.createFromLlmEvent`: маппить `sourceMessageIds` → `ChatMessage`

## Technical Notes

* `ChatMessage.java`: `backend/monolith/src/main/java/ru/team42/monolith/entity/ChatMessage.java`
* `ChatMessageRepository.java`: текущие запросы по `chatId` — нужно переписать на `team`
* `ChatMessageBatchingService.java`: `findDistinctChatIdsWithUnprocessedMessages` → заменить на поиск по `team`
* `ChatMessageMapper.java`: убрать `@Mapping(source = "event.chatId", target = "chatId")`
* `message_batch.proto`: `core/kafka-proto-common/src/main/proto/ru/team42/events/message_batch.proto`
* `ChatMessageBatchPublisher.java`: уже не использует protobuf-маппинг через MapStruct, прямой builder
* `LlmTaskCreateEvent.java`: помечен `@JsonIgnoreProperties(ignoreUnknown = true)` — новое поле безопасно добавляется
* Spring Boot 3 / Hibernate 6: `@ManyToMany` без дополнительных зависимостей
