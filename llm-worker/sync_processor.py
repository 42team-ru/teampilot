from loguru import logger

from infra.kafka import publish
from infra.qdrant import search_tasks
from llm.chains import sync_split_chain
from models import SyncDraftEvent, SyncDraftItem, SyncRequestEvent
from settings import settings

TOPIC_SYNC_DRAFT = "sync.draft"


def _split_into_tasks(raw_text: str) -> list[str]:
    text = raw_text.strip()
    if not text:
        return []
    try:
        result = sync_split_chain.invoke({"text": text})
        if isinstance(result, list) and all(isinstance(x, str) and x.strip() for x in result) and result:
            return [x.strip() for x in result]
    except Exception as e:
        logger.warning(f"[SYNC] Task splitting failed: {e}")
    # Fallback: treat the whole report as a single task
    return [text]


def _process_single_line(
    line: str,
    event: SyncRequestEvent,
    active_by_id: dict,
    candidates_limit: int = 10,
) -> list[SyncDraftItem]:
    items: list[SyncDraftItem] = []

    candidates = sorted(
        search_tasks(line, event.team_id, limit=candidates_limit),
        key=lambda c: c["score"],
        reverse=True,
    )

    top = candidates[0] if candidates else None
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
    confident = (
        top is not None
        and top["score"] >= settings.SYNC_MATCH_THRESHOLD
        and (top["score"] - second_score) >= settings.SYNC_MATCH_MARGIN
    )

    logger.debug(
        f"[SYNC] Qdrant top_score={top['score'] if top else None} "
        f"second_score={second_score} confident={confident} "
        f"candidates={len(candidates)} for line={line!r:.80}"
    )

    if confident:
        task_id = top["task_id"]
        task = active_by_id.get(task_id)
        title = task.title if task else top["title"]
        items.append(SyncDraftItem(
            index=0,
            user_text=line,
            task_id=task_id,
            task_title=title,
            is_new_task=False,
        ))

    if not items:
        logger.info(f"[SYNC] No confident qdrant match — treating as new task for requestId={event.request_id}")
        items.append(SyncDraftItem(
            index=0,
            user_text=line,
            task_id=None,
            task_title=line,
            is_new_task=True,
        ))

    return items


def process_sync_request(event: SyncRequestEvent) -> None:
    logger.info(
        f"[SYNC] requestId={event.request_id} user={event.telegram_user_id} "
        f"tasks={len(event.active_tasks)} text={event.raw_text!r:.80}"
    )

    active_by_id = {t.id: t for t in event.active_tasks}

    task_descriptions = _split_into_tasks(event.raw_text)

    items: list[SyncDraftItem] = []
    for description in task_descriptions:
        items.extend(_process_single_line(description, event, active_by_id))

    for idx, item in enumerate(items, start=1):
        item.index = idx

    draft = SyncDraftEvent(
        request_id=event.request_id,
        team_id=event.team_id,
        telegram_user_id=event.telegram_user_id,
        items=items,
    )
    publish(TOPIC_SYNC_DRAFT, draft, key=event.request_id)
    logger.info(f"[SYNC] Draft published requestId={event.request_id} items={len(items)}")
