import functools
import re
import uuid

from langchain_openai import OpenAIEmbeddings
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from settings import settings


@functools.lru_cache(maxsize=1)
def _embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDINGS_MODEL,
        base_url=settings.EMBEDDINGS_API_BASE,
        api_key=settings.EMBEDDINGS_API_KEY,
        check_embedding_ctx_length=False,
    )


@functools.lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


_TASK_POINT_NAMESPACE = uuid.UUID("ea185060-8485-4f07-a957-28d556640727")
_KNOWLEDGE_POINT_NAMESPACE = uuid.UUID("c3f1a2b4-9d7e-4f8c-a1b2-3d4e5f6a7b8c")
_TASK_VECTOR_KINDS = ("summary", "title", "description", "status")
_STATUS_ACTIONS = (
    "готово",
    "сделал",
    "сделала",
    "доделал",
    "доделала",
    "закрыл",
    "закрыла",
    "закончил",
    "закончила",
    "беру",
    "взял",
    "взяла",
    "в работе",
    "отменяем",
    "отменить",
)
_DESCRIPTION_SNIPPET_CHARS = 260


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_description(description: str | None) -> str:
    lines = []
    for line in (description or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Уверенность ИИ:"):
            continue
        lines.append(stripped)
    return _normalize_text(" ".join(lines))


def _snippet(value: str | None, limit: int = _DESCRIPTION_SNIPPET_CHARS) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _task_point_id(task_id: str, kind: str) -> str:
    return str(uuid.uuid5(_TASK_POINT_NAMESPACE, f"{task_id}:{kind}"))


def _task_point_ids(task_id: str) -> list[str]:
    # Keep the raw task_id too so deletes clean up points written by the old
    # single-vector implementation.
    return [
        task_id,
        *[_task_point_id(task_id, kind) for kind in _TASK_VECTOR_KINDS],
    ]


def _task_representations(title: str, description: str | None) -> list[tuple[str, str]]:
    clean_title = _normalize_text(title)
    clean_description = _clean_description(description)

    representations = [
        (
            "summary",
            _normalize_text(f"Задача: {clean_title}. Описание: {clean_description}"),
        ),
        (
            "title",
            _normalize_text(
                f"Название задачи: {clean_title}. "
                f"Ключевые слова задачи: {clean_title}"
            ),
        ),
    ]

    if clean_description:
        representations.append((
            "description",
            _normalize_text(f"Описание задачи \"{clean_title}\": {clean_description}"),
        ))

    status_phrases = "; ".join(f"{action} {clean_title}" for action in _STATUS_ACTIONS)
    representations.append((
        "status",
        _normalize_text(
            f"Статусные фразы по задаче \"{clean_title}\": {status_phrases}"
        ),
    ))

    return [(kind, text) for kind, text in representations if text]


def _embed_documents(texts: list[str]) -> list[list[float]]:
    embedder = _embedder()
    if hasattr(embedder, "embed_documents"):
        return embedder.embed_documents(texts)
    return [embedder.embed_query(text) for text in texts]


def _query_task_points(
    query: str,
    team_id: str,
    limit: int,
    score_threshold: float | None,
) -> list:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return []

    vector = _embedder().embed_query(normalized_query)
    raw = get_qdrant_client().query_points(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        query=vector,
        limit=max(limit * len(_TASK_VECTOR_KINDS) * 2, limit),
        score_threshold=None,
        query_filter=Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        ),
    )
    all_points = list(raw.points)
    if all_points:
        top_scores = ", ".join(
            f"{p.payload.get('kind', '?')}={p.score:.3f}" for p in all_points[:5]
        )
        logger.debug(
            "task search query={!r} threshold={} top_scores=[{}]",
            query[:80],
            score_threshold,
            top_scores,
        )
    return [p for p in all_points if score_threshold is None or p.score >= score_threshold]


def _aggregate_task_points(points: list, limit: int) -> list[dict]:
    candidates: dict[str, dict] = {}

    for point in points:
        payload = point.payload or {}
        task_id = payload.get("task_id")
        if not task_id:
            continue

        score = float(point.score or 0.0)
        candidate = candidates.setdefault(
            task_id,
            {
                "task_id": task_id,
                "title": payload.get("title") or "",
                "description": payload.get("description") or "",
                "score": score,
                "rank_score": score,
                "matched_kind": payload.get("kind") or "unknown",
                "matched_text": payload.get("text") or "",
                "matches": [],
            },
        )

        if score > candidate["score"]:
            candidate["score"] = score
            candidate["matched_kind"] = payload.get("kind") or "unknown"
            candidate["matched_text"] = payload.get("text") or ""

        if not candidate.get("title") and payload.get("title"):
            candidate["title"] = payload["title"]
        if not candidate.get("description") and payload.get("description"):
            candidate["description"] = payload["description"]

        candidate["matches"].append({
            "kind": payload.get("kind") or "unknown",
            "score": score,
        })

    for candidate in candidates.values():
        candidate["matches"].sort(key=lambda match: match["score"], reverse=True)
        match_boost = min(0.03 * (len(candidate["matches"]) - 1), 0.09)
        candidate["rank_score"] = candidate["score"] + match_boost
        candidate["description"] = _snippet(candidate.get("description"))
        candidate["matched_text"] = _snippet(candidate.get("matched_text"))

    return sorted(
        candidates.values(),
        key=lambda candidate: (candidate["rank_score"], candidate["score"]),
        reverse=True,
    )[:limit]


def ensure_collections() -> None:
    client = get_qdrant_client()
    for name in [settings.QDRANT_COLLECTION_TASKS, settings.QDRANT_COLLECTION_KNOWLEDGE]:
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDINGS_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {name}")
        client.create_payload_index(
            collection_name=name,
            field_name="team_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

    client.create_payload_index(
        collection_name=settings.QDRANT_COLLECTION_KNOWLEDGE,
        field_name="type",
        field_schema=PayloadSchemaType.KEYWORD,
    )


def store_task(task_id: str, title: str, description: str, team_id: str) -> None:
    try:
        clean_title = _normalize_text(title)
        clean_description = _clean_description(description)
        representations = _task_representations(clean_title, clean_description)
        vectors = _embed_documents([text for _, text in representations])

        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points=[
                PointStruct(
                    id=_task_point_id(task_id, kind),
                    vector=vector,
                    payload={
                        "task_id": task_id,
                        "title": clean_title,
                        "description": clean_description,
                        "team_id": team_id,
                        "kind": kind,
                        "text": text,
                    },
                )
                for (kind, text), vector in zip(representations, vectors)
            ],
        )
    except Exception as e:
        logger.opt(exception=True).warning(
            "store_task failed (task_id={}): {}",
            task_id,
            e,
        )


def delete_task(task_id: str) -> None:
    try:
        get_qdrant_client().delete(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points_selector=PointIdsList(points=_task_point_ids(task_id)),
        )
        logger.debug("Deleted task {} from Qdrant", task_id)
    except Exception as e:
        logger.opt(exception=True).warning(
            "delete_task failed (task_id={}): {}",
            task_id,
            e,
        )


def search_tasks(
    query: str,
    team_id: str,
    limit: int = 5,
    score_threshold: float | None = None,
) -> list[dict]:
    """Return top-N active tasks for a team ranked by semantic similarity to query."""
    try:
        threshold = (
            settings.STATUS_HINT_THRESHOLD
            if score_threshold is None
            else score_threshold
        )
        points = _query_task_points(
            query,
            team_id,
            limit=limit,
            score_threshold=threshold,
        )
        return _aggregate_task_points(points, limit=limit)
    except Exception as e:
        logger.opt(exception=True).warning(
            "search_tasks failed for team {}: {}",
            team_id,
            e,
        )
        return []


def is_task_duplicate(title: str, description: str, team_id: str) -> bool:
    try:
        query = _normalize_text(f"{title}\n{_clean_description(description)}")
        points = _query_task_points(
            query,
            team_id,
            limit=1,
            score_threshold=settings.DEDUP_THRESHOLD,
        )
        candidates = _aggregate_task_points(points, limit=1)
        if candidates:
            top = candidates[0]
            logger.debug(
                "Duplicate found for {!r}: task_id={} score={:.3f} matched_kind={}",
                title,
                top["task_id"],
                top["score"],
                top["matched_kind"],
            )
        return bool(candidates)
    except Exception as e:
        logger.opt(exception=True).warning(
            "is_task_duplicate failed for {!r}: {}",
            title,
            e,
        )


# ─── Knowledge base ───────────────────────────────────────────────────────────

def _knowledge_point_id(source_id: str) -> str:
    return str(uuid.uuid5(_KNOWLEDGE_POINT_NAMESPACE, source_id))


def store_knowledge(
    source_id: str,
    team_id: str,
    knowledge_type: str,
    content: str,
    title: str = "",
) -> None:
    try:
        text = _normalize_text(content)
        if not text:
            return
        vector = _embedder().embed_query(text)
        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION_KNOWLEDGE,
            points=[
                PointStruct(
                    id=_knowledge_point_id(source_id),
                    vector=vector,
                    payload={
                        "source_id": source_id,
                        "team_id": team_id,
                        "type": knowledge_type,
                        "content": text,
                        "title": _normalize_text(title),
                    },
                )
            ],
        )
        logger.debug("store_knowledge source_id={} type={} team={}", source_id, knowledge_type, team_id)
    except Exception as e:
        logger.opt(exception=True).warning(
            "store_knowledge failed (source_id={}): {}",
            source_id,
            e,
        )


def delete_knowledge(source_id: str) -> None:
    try:
        get_qdrant_client().delete(
            collection_name=settings.QDRANT_COLLECTION_KNOWLEDGE,
            points_selector=PointIdsList(points=[_knowledge_point_id(source_id)]),
        )
        logger.debug("delete_knowledge source_id={}", source_id)
    except Exception as e:
        logger.opt(exception=True).warning(
            "delete_knowledge failed (source_id={}): {}",
            source_id,
            e,
        )


def search_knowledge(
    query: str,
    team_id: str,
    knowledge_type: str | None = None,
    limit: int = 3,
) -> list[dict]:
    try:
        normalized = _normalize_text(query)
        if not normalized:
            return []
        vector = _embedder().embed_query(normalized)
        must = [FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        if knowledge_type:
            must.append(FieldCondition(key="type", match=MatchValue(value=knowledge_type)))
        response = get_qdrant_client().query_points(
            collection_name=settings.QDRANT_COLLECTION_KNOWLEDGE,
            query=vector,
            limit=limit,
            query_filter=Filter(must=must),
        )
        results = [
            {
                "source_id": p.payload.get("source_id", ""),
                "type": p.payload.get("type", ""),
                "title": p.payload.get("title", ""),
                "content": _snippet(p.payload.get("content", "")),
                "score": float(p.score or 0.0),
            }
            for p in response.points
            if p.payload
        ]
        if results:
            scores_summary = ", ".join(
                f"{r['type']}:{r['score']:.3f} {r['title'][:30]!r}" for r in results
            )
            logger.debug("knowledge search query={!r} team={} hits=[{}]", query[:80], team_id, scores_summary)
        else:
            logger.debug("knowledge search query={!r} team={} hits=[]", query[:80], team_id)
        return results
    except Exception as e:
        logger.opt(exception=True).warning(
            "search_knowledge failed for team {}: {}",
            team_id,
            e,
        )
        return []
