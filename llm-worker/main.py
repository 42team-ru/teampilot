import uuid
from typing import List, Optional, Union

from loguru import logger
from pydantic import ValidationError

from infra.kafka import BatchConsumer, flush, publish
from infra.qdrant import is_task_duplicate, store_batch, store_task
from llm.chains import classifier_chain, status_chain, task_chain
from models import (
    ClassificationResult,
    MessageBatchEvent,
    StatusChangeEvent,
    StatusExtractionList,
    TaskCreateEvent,
    TaskExtractionList,
    TeamMember,
    proto_to_batch_event,
)
from proto_generated.ru.team42.events import message_batch_pb2
from settings import settings

# Kafka Topic Constants
TOPIC_IN = "messages.batches"
TOPIC_TASKS = "llm.tasks.create"
TOPIC_STATUS = "llm.status.change"


def format_messages(batch: MessageBatchEvent) -> str:
    """
    Formats a batch of messages into a single string for LLM consumption.
    
    Args:
        batch: The message batch event containing individual messages.
        
    Returns:
        A formatted string with timestamps and usernames.
    """
    return "\n".join(
        f"[{m.timestamp.strftime('%H:%M')}] {m.username or m.full_name}: {m.text}"
        for m in batch.messages
    )


def format_team_context(batch: MessageBatchEvent) -> str:
    """
    Formats the team list into a readable context for the LLM.
    Includes Russian role synonyms to help LLaMA match slangy references.
    """
    if not batch.team:
        return "TEAM LIST: not provided (use chat log usernames only)"

    # Russian synonyms help LLaMA 8B map "девопс" → DevOps, "фронт" → Frontend, etc.
    role_synonyms: dict[str, str] = {
        "devops": "девопс",
        "developer": "разработчик",
        "frontend": "фронтенд/фронт",
        "backend": "бэкенд/бэк",
        "qa": "тестировщик/QA",
        "pm": "менеджер/PM",
        "lead": "лид/тимлид",
        "designer": "дизайнер",
    }

    lines = ["TEAM LIST (use this to resolve names and roles to @username):"]
    for m in batch.team:
        username = m.username if m.username.startswith("@") else f"@{m.username}"
        synonym = role_synonyms.get(m.role.lower(), "")
        role_display = f"{m.role} ({synonym})" if synonym else m.role
        lines.append(f"  - {username}  |  {m.full_name}  |  {role_display}")
    return "\n".join(lines)


def resolve_assignee_id(assignee: str | None, team: list[TeamMember]) -> int | None:
    """
    Looks up the user_id from the team list based on the assignee username.
    """
    if not assignee or not team:
        return None
    
    # Normalize assignee (e.g., "@username" -> "username")
    assignee_clean = assignee.lstrip("@").lower()
    
    for member in team:
        if member.username.lstrip("@").lower() == assignee_clean:
            return member.user_id
            
    return None


def process_batch(batch: MessageBatchEvent) -> List[Union[TaskCreateEvent, StatusChangeEvent]]:
    """
    Core logic for processing a message batch.
    
    This function:
    1. Formats messages.
    2. Stores the batch in Qdrant for context/RAG.
    3. Runs a cheap classifier to detect tasks or status changes.
    4. If detected, runs expensive extraction chains.
    5. Returns a list of generated events.
    
    Args:
        batch: The input message batch from Kafka or direct call.
        
    Returns:
        A list of events (TaskCreateEvent or StatusChangeEvent) to be published or processed.
    """
    text = format_messages(batch)
    
    # Store in Qdrant for future RAG context
    # Note: store_batch is currently a placeholder in infra/qdrant.py
    store_batch(batch.event_id, text, batch.chat_id)

    results = []

    try:
        # Step 1: Classification (Cheap LLM)
        clf_output = classifier_chain.invoke({"messages": text})
        clf = ClassificationResult.model_validate(clf_output)
    except (ValidationError, Exception) as e:
        logger.error(f"Classifier failed (batch={batch.event_id}): {e}")
        return results

    logger.debug(f"Classification for batch {batch.event_id}: {clf}")

    # Step 2: Task Extraction (Expensive LLM)
    if clf.has_task and clf.confidence_task >= settings.CLASSIFIER_THRESHOLD:
        task_events = _extract_tasks(batch, text)
        results.extend(task_events)

    # Step 3: Status Change Extraction (Expensive LLM)
    if clf.has_status_change and clf.confidence_status >= settings.CLASSIFIER_THRESHOLD:
        status_events = _extract_statuses(batch, text)
        results.extend(status_events)

    return results


def _extract_tasks(batch: MessageBatchEvent, text: str) -> List[TaskCreateEvent]:
    """
    Extracts one or more tasks from the batch text.
    Uses TaskExtractionList for per-item fault tolerance.
    """
    try:
        raw = task_chain.invoke({
            "messages": text,
            "current_datetime": batch.occurred_at.isoformat(),
            "team_context": format_team_context(batch),
        })
        extraction_list = TaskExtractionList.model_validate(raw)

        if extraction_list.failed_items > 0:
            logger.warning(
                f"Task extraction: {extraction_list.failed_items} item(s) failed "
                f"validation and were skipped (batch={batch.event_id})"
            )

        events = []
        for extraction in extraction_list.tasks:
            if is_task_duplicate(extraction.title, extraction.description or ""):
                logger.info(f"Duplicate task skipped: {extraction.title!r}")
                continue

            task_id = str(uuid.uuid4())
            store_task(task_id, extraction.title, extraction.description or "")
            
            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            
            events.append(TaskCreateEvent(
                chat_id=batch.chat_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                **extraction.model_dump(),
            ))

        return events
    except Exception as e:
        logger.error(f"Task extraction chain failed (batch={batch.event_id}): {e}")
        return []


def _extract_statuses(batch: MessageBatchEvent, text: str) -> List[StatusChangeEvent]:
    """
    Extracts one or more status changes from the batch text.
    Uses StatusExtractionList for per-item fault tolerance.
    """
    try:
        raw = status_chain.invoke({
            "messages": text,
            "team_context": format_team_context(batch),
        })
        extraction_list = StatusExtractionList.model_validate(raw)

        if extraction_list.failed_items > 0:
            logger.warning(
                f"Status extraction: {extraction_list.failed_items} item(s) failed "
                f"validation and were skipped (batch={batch.event_id})"
            )

        events = []
        for extraction in extraction_list.statuses:
            assignee_id = resolve_assignee_id(extraction.assignee, batch.team)
            events.append(StatusChangeEvent(
                chat_id=batch.chat_id,
                source_batch_id=batch.event_id,
                assignee_id=assignee_id,
                **extraction.model_dump(),
            ))
        return events
    except Exception as e:
        logger.error(f"Status extraction chain failed (batch={batch.event_id}): {e}")
        return []



def main() -> None:
    """
    Kafka Consumer loop entry point.
    """
    logger.info("LLM Worker starting in Kafka Consumer mode...")

    consumer = BatchConsumer(TOPIC_IN)
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
                
            try:
                # Parse incoming batch
                proto_event = message_batch_pb2.MessageBatchEvent()
                proto_event.ParseFromString(msg.value())
                batch = proto_to_batch_event(proto_event)
                logger.info(f"Processing batch {batch.event_id} ({len(batch.messages)} msgs) from chat {batch.chat_id}")
                
                # Process the batch and get results
                events = process_batch(batch)
                
                # Publish results to respective Kafka topics
                for event in events:
                    if isinstance(event, TaskCreateEvent):
                        publish(TOPIC_TASKS, event, key=str(batch.chat_id))
                        logger.info(f"Task event published: {event.title!r}")
                    elif isinstance(event, StatusChangeEvent):
                        publish(TOPIC_STATUS, event, key=str(batch.chat_id))
                        logger.info(f"Status event published: {event.action}")

                # Коммитим offset только после успешной публикации
                # (в finally было бы потеря сообщений при любой ошибке)
                consumer.commit(msg)

            except Exception as e:
                logger.error(f"Error processing message from Kafka: {e}")
                # Намеренно не коммитим — сообщение будет переобработано
                
    except KeyboardInterrupt:
        logger.info("Graceful shutdown initiated...")
    finally:
        consumer.close()
        flush()


if __name__ == "__main__":
    main()
