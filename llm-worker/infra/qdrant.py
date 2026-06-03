"""
Qdrant store с локальными эмбеддингами через FastEmbed.
Модель скачивается автоматически при первом запуске (~60 MB).
"""
import uuid

from loguru import logger
from qdrant_client import QdrantClient

from settings import settings

import functools

@functools.lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(url=settings.QDRANT_URL)
    client.set_model(settings.FASTEMBED_MODEL)
    return client


def store_batch(batch_id: str, text: str, chat_id: int) -> None:
#     _client.add(
#         collection_name=settings.QDRANT_COLLECTION_BATCHES,
#         documents=[text],
#         ids=[str(uuid.uuid5(uuid.NAMESPACE_URL, batch_id))],
#         metadata=[{"batch_id": batch_id, "chat_id": chat_id}],
#     )
    pass


def is_task_duplicate(title: str, description: str) -> bool:
    pass
#     results = _client.query(
#         collection_name=settings.QDRANT_COLLECTION_TASKS,
#         query_text=f"{title}\n{description}",
#         limit=1,
#         score_threshold=settings.DEDUP_THRESHOLD,
#     )
#     if results:
#         logger.debug(f"Duplicate found for {title!r}, score={results[0].score:.3f}")
#     return bool(results)


def store_task(task_id: str, title: str, description: str) -> None:
    pass
#     _client.add(
#         collection_name=settings.QDRANT_COLLECTION_TASKS,
#         documents=[f"{title}\n{description}"],
#         ids=[task_id],
#         metadata=[{"title": title}],
#     )
