"""
Qdrant store с локальными эмбеддингами через FastEmbed.
Модель скачивается автоматически при первом запуске (~60 MB).
"""
import uuid

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from settings import settings

import functools


@functools.lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(url=settings.QDRANT_URL)
    client.set_model(settings.FASTEMBED_MODEL)
    return client


def init_collections() -> None:
    client = get_qdrant_client()
    for name in [settings.QDRANT_COLLECTION_TASKS, settings.QDRANT_COLLECTION_BATCHES]:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=client.get_fastembed_vector_params(),
            )
            logger.info(f"Created Qdrant collection: {name}")


def store_batch(batch_id: str, text: str, team_id: str) -> None:
    try:
        get_qdrant_client().add(
            collection_name=settings.QDRANT_COLLECTION_BATCHES,
            documents=[text],
            ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, batch_id))],
            metadata=[{"batch_id": batch_id, "team_id": team_id}],
        )
    except Exception as e:
        logger.warning(f"store_batch failed (batch={batch_id}): {e}")


def is_task_duplicate(title: str, description: str, team_id: str) -> bool:
    try:
        results = get_qdrant_client().query(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            query_text=f"{title}\n{description}",
            limit=1,
            score_threshold=settings.DEDUP_THRESHOLD,
            query_filter=Filter(
                must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
            ),
        )
        if results:
            logger.debug(f"Duplicate found for {title!r}, score={results[0].score:.3f}")
        return bool(results)
    except Exception as e:
        logger.warning(f"is_task_duplicate failed for {title!r}: {e}")
        return False


def store_task(task_id: str, title: str, description: str, team_id: str) -> None:
    try:
        get_qdrant_client().add(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            documents=[f"{title}\n{description}"],
            ids=[task_id],
            metadata=[{"task_id": task_id, "title": title, "team_id": team_id, "status": "TODO"}],
        )
    except Exception as e:
        logger.warning(f"store_task failed (task_id={task_id}): {e}")


def find_task_by_hint(task_hint: str, team_id: str) -> str | None:
    """Находит task_id по краткому хинту от LLM для резолвинга статус-изменений."""
    try:
        results = get_qdrant_client().query(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            query_text=task_hint,
            limit=1,
            score_threshold=settings.STATUS_HINT_THRESHOLD,
            query_filter=Filter(
                must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
            ),
        )
        if results:
            found_id = results[0].metadata.get("task_id")
            logger.debug(f"Resolved hint {task_hint!r} → task_id={found_id}, score={results[0].score:.3f}")
            return found_id
        return None
    except Exception as e:
        logger.warning(f"find_task_by_hint failed for {task_hint!r}: {e}")
        return None
