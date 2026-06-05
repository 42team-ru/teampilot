import functools

from langchain_openai import OpenAIEmbeddings
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointIdsList, PointStruct, VectorParams

from settings import settings


@functools.lru_cache(maxsize=1)
def _embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDINGS_MODEL,
        base_url=settings.EMBEDDINGS_API_BASE,
        api_key=settings.EMBEDDINGS_API_KEY,
    )


@functools.lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def init_collections() -> None:
    client = get_qdrant_client()
    for name in [settings.QDRANT_COLLECTION_TASKS]:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=settings.EMBEDDINGS_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {name}")


def store_task(task_id: str, title: str, description: str, team_id: str) -> None:
    try:
        vector = _embedder().embed_query(f"{title}\n{description}")
        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points=[PointStruct(
                id=task_id,
                vector=vector,
                payload={"task_id": task_id, "title": title, "team_id": team_id},
            )],
        )
    except Exception as e:
        logger.warning(f"store_task failed (task_id={task_id}): {e}")


def delete_task(task_id: str) -> None:
    try:
        get_qdrant_client().delete(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points_selector=PointIdsList(points=[task_id]),
        )
        logger.debug(f"Deleted task {task_id} from Qdrant")
    except Exception as e:
        logger.warning(f"delete_task failed (task_id={task_id}): {e}")


def is_task_duplicate(title: str, description: str, team_id: str) -> bool:
    try:
        vector = _embedder().embed_query(f"{title}\n{description}")
        results = get_qdrant_client().search(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            query_vector=vector,
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
