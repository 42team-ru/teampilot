import json

from langchain_openai import ChatOpenAI
from loguru import logger

from infra.kafka import publish
from infra.qdrant import search_tasks
from models import SyncDraftEvent, SyncDraftItem, SyncRequestEvent
from settings import settings

TOPIC_SYNC_DRAFT = "sync.draft"

_MATCH_PROMPT = """Пользователь написал что сделал: "{text}"

Активные задачи:
{tasks}

Найди задачи, которые ПРЯМО И ОДНОЗНАЧНО упомянуты в тексте пользователя.
Правила:
- Совпадение должно быть явным, не косвенным
- Если текст упоминает одно конкретное действие — верни максимум 1 задачу
- Если задача не упомянута точно — НЕ включай её
- Верни ТОЛЬКО JSON-массив id. Если ничего не подходит — верни []

Пример: ["uuid1"] или []"""


def _cheap_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_CHEAP_MODEL,
        base_url=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        temperature=0,
    )


def _llm_match_tasks(raw_text: str, active_tasks: list) -> list[str]:
    if not active_tasks:
        return []
    tasks_json = json.dumps(
        [{"id": t.id, "title": t.title, "description": (t.description or "")[:120]}
         for t in active_tasks],
        ensure_ascii=False,
    )
    prompt = _MATCH_PROMPT.format(text=raw_text, tasks=tasks_json)
    try:
        response = _cheap_llm().invoke(prompt)
        content = response.content.strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            matched = json.loads(content[start:end])
            valid_ids = {t.id for t in active_tasks}
            return [str(m) for m in matched if isinstance(m, str) and m in valid_ids]
    except Exception as e:
        logger.warning(f"[SYNC] LLM matching failed: {e}")
    return []


def process_sync_request(event: SyncRequestEvent) -> None:
    logger.info(
        f"[SYNC] requestId={event.request_id} user={event.telegram_user_id} "
        f"tasks={len(event.active_tasks)} text={event.raw_text!r:.80}"
    )

    candidates = search_tasks(event.raw_text, event.team_id, limit=10)
    matched_ids = {
        c["task_id"]
        for c in candidates
        if c["score"] >= settings.STATUS_HINT_THRESHOLD
    }
    logger.debug(
        f"[SYNC] Qdrant matched {len(matched_ids)}/{len(candidates)} tasks "
        f"above threshold={settings.STATUS_HINT_THRESHOLD}"
    )

    active_by_id = {t.id: t for t in event.active_tasks}
    items: list[SyncDraftItem] = []
    index = 1

    for task_id in matched_ids:
        task = active_by_id.get(task_id)
        title = task.title if task else next(
            (c["title"] for c in candidates if c["task_id"] == task_id), task_id
        )
        items.append(SyncDraftItem(
            index=index,
            user_text=event.raw_text,
            task_id=task_id,
            task_title=title,
            is_new_task=False,
        ))
        index += 1

    if not items and event.active_tasks:
        logger.info(f"[SYNC] Qdrant empty — falling back to LLM matching for requestId={event.request_id}")
        llm_ids = _llm_match_tasks(event.raw_text, event.active_tasks)
        logger.info(f"[SYNC] LLM matched task_ids={llm_ids}")
        for task_id in llm_ids:
            task = active_by_id.get(task_id)
            if task:
                items.append(SyncDraftItem(
                    index=index,
                    user_text=event.raw_text,
                    task_id=task_id,
                    task_title=task.title,
                    is_new_task=False,
                ))
                index += 1

    if not items:
        logger.info(f"[SYNC] No tasks matched — marking as new task for requestId={event.request_id}")
        items.append(SyncDraftItem(
            index=1,
            user_text=event.raw_text,
            task_id=None,
            task_title=event.raw_text,
            is_new_task=True,
        ))

    draft = SyncDraftEvent(
        request_id=event.request_id,
        team_id=event.team_id,
        telegram_user_id=event.telegram_user_id,
        items=items,
    )
    publish(TOPIC_SYNC_DRAFT, draft, key=event.request_id)
    logger.info(f"[SYNC] Draft published requestId={event.request_id} items={len(items)}")
