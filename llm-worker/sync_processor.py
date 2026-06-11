import json

from loguru import logger

from infra.kafka import publish
from infra.qdrant import search_tasks
from llm.chains import sync_match_chain
from models import SyncDraftEvent, SyncDraftItem, SyncRequestEvent
from settings import settings

TOPIC_SYNC_DRAFT = "sync.draft"


def _llm_match_tasks(raw_text: str, active_tasks: list) -> list[str]:
    if not active_tasks:
        return []
    tasks_json = json.dumps(
        [{"id": t.id, "title": t.title, "description": (t.description or "")[:120]}
         for t in active_tasks],
        ensure_ascii=False,
    )
    try:
        result = sync_match_chain.invoke({"text": raw_text, "tasks": tasks_json})
        if not isinstance(result, list):
            return []
        valid_ids = {t.id for t in active_tasks}
        return [m for m in result if isinstance(m, str) and m in valid_ids]
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

    for idx, task_id in enumerate(matched_ids, start=1):
        task = active_by_id.get(task_id)
        title = task.title if task else next(
            (c["title"] for c in candidates if c["task_id"] == task_id), task_id
        )
        items.append(SyncDraftItem(
            index=idx,
            user_text=event.raw_text,
            task_id=task_id,
            task_title=title,
            is_new_task=False,
        ))

    if not items and event.active_tasks:
        logger.info(f"[SYNC] Qdrant empty — falling back to LLM for requestId={event.request_id}")
        llm_ids = _llm_match_tasks(event.raw_text, event.active_tasks)
        logger.info(f"[SYNC] LLM matched task_ids={llm_ids}")
        for idx, task_id in enumerate(llm_ids, start=1):
            task = active_by_id.get(task_id)
            if task:
                items.append(SyncDraftItem(
                    index=idx,
                    user_text=event.raw_text,
                    task_id=task_id,
                    task_title=task.title,
                    is_new_task=False,
                ))

    if not items:
        logger.info(f"[SYNC] No tasks matched — treating as new task for requestId={event.request_id}")
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
