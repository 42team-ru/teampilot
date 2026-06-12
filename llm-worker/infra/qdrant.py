import functools
import re
import uuid

from fastembed import SparseTextEmbedding
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    MinShould,
    PayloadSchemaType,
    PointIdsList,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from infra.rerank import rerank as _rerank
from settings import settings

# Именованные векторы в коллекциях: dense (семантика) + bm25 (лексика).
_DENSE = "dense"
_SPARSE = "bm25"


@functools.lru_cache(maxsize=1)
def _embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDINGS_MODEL,
        base_url=settings.EMBEDDINGS_API_BASE,
        api_key=settings.EMBEDDINGS_API_KEY,
        check_embedding_ctx_length=False,
    )


@functools.lru_cache(maxsize=1)
def _bm25() -> SparseTextEmbedding:
    try:
        return SparseTextEmbedding(settings.BM25_MODEL, language=settings.BM25_LANGUAGE)
    except TypeError:
        # старые версии fastembed без kwarg language
        return SparseTextEmbedding(settings.BM25_MODEL)


@functools.lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


_TASK_POINT_NAMESPACE = uuid.UUID("ea185060-8485-4f07-a957-28d556640727")
_KNOWLEDGE_POINT_NAMESPACE = uuid.UUID("c3f1a2b4-9d7e-4f8c-a1b2-3d4e5f6a7b8c")
# Legacy: старая реализация писала по 4 точки-представления на задачу.
_LEGACY_TASK_VECTOR_KINDS = ("summary", "title", "description", "status")
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


def _task_point_id(task_id: str) -> str:
    return str(uuid.uuid5(_TASK_POINT_NAMESPACE, task_id))


def _legacy_task_point_ids(task_id: str) -> list[str]:
    # Чистим точки, записанные старой single-vector и multi-vector реализациями.
    return [
        task_id,
        *[
            str(uuid.uuid5(_TASK_POINT_NAMESPACE, f"{task_id}:{kind}"))
            for kind in _LEGACY_TASK_VECTOR_KINDS
        ],
    ]


def _task_text(title: str, description: str) -> str:
    title = _normalize_text(title)
    description = _clean_description(description)
    if description:
        return _normalize_text(f"Задача: {title}. Описание: {description}")
    return _normalize_text(f"Задача: {title}")


# ─── Эмбеддинги ────────────────────────────────────────────────────────────────

def _dense_doc(text: str) -> list[float]:
    embedder = _embedder()
    if hasattr(embedder, "embed_documents"):
        return embedder.embed_documents([text])[0]
    return embedder.embed_query(text)


def _dense_query(text: str) -> list[float]:
    return _embedder().embed_query(text)


def _sparse_doc(text: str) -> SparseVector:
    emb = next(_bm25().passage_embed([text]))
    return SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())


def _sparse_query(text: str) -> SparseVector:
    emb = next(_bm25().query_embed([text]))
    return SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())


# ─── Поиск (hybrid + RRF, опц. rerank) ─────────────────────────────────────────

def _hybrid_points(
    collection: str,
    query: str,
    query_filter: Filter | None,
    candidates: int,
) -> list:
    """Достать кандидатов через dense+bm25 prefetch, слитых RRF (recall-этап)."""
    normalized = _normalize_text(query)
    if not normalized:
        return []
    raw = get_qdrant_client().query_points(
        collection_name=collection,
        prefetch=[
            Prefetch(
                query=_dense_query(normalized),
                using=_DENSE,
                limit=candidates,
                filter=query_filter,
            ),
            Prefetch(
                query=_sparse_query(normalized),
                using=_SPARSE,
                limit=candidates,
                filter=query_filter,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=candidates,
    )
    return list(raw.points)


def _dense_points(
    collection: str,
    query: str,
    query_filter: Filter | None,
    limit: int,
    score_threshold: float | None,
) -> list:
    """Чистый dense-поиск с косинус-порогом — для дедупа (абсолютная похожесть)."""
    normalized = _normalize_text(query)
    if not normalized:
        return []
    raw = get_qdrant_client().query_points(
        collection_name=collection,
        query=_dense_query(normalized),
        using=_DENSE,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=query_filter,
    )
    return list(raw.points)


def _apply_rerank(
    query: str,
    candidates: list[dict],
    limit: int,
) -> tuple[list[dict], bool]:
    """Пересортировать кандидатов реранкером (precision). Возврат (items, reranked?)."""
    if not candidates:
        return [], False
    order = _rerank(query, [c["_doc"] for c in candidates], top_n=limit)
    if not order:
        return candidates[:limit], False
    reranked = []
    for idx, relevance in order:
        if 0 <= idx < len(candidates):
            item = candidates[idx]
            item["score"] = relevance
            item["rank_score"] = relevance
            item["matched_kind"] = "rerank"
            reranked.append(item)
    return reranked[:limit], True


def _task_dict(point) -> dict:
    payload = point.payload or {}
    score = float(point.score or 0.0)
    return {
        "task_id": payload.get("task_id", ""),
        "title": payload.get("title", ""),
        "description": _snippet(payload.get("description", "")),
        "score": score,
        "rank_score": score,
        "matched_kind": "hybrid",
        "matched_text": _snippet(payload.get("text", "")),
        "matches": [],
        "_doc": payload.get("text") or payload.get("title", ""),
    }


def _is_hybrid_collection(client: QdrantClient, name: str) -> bool:
    """True, если коллекция уже на новой схеме (named dense + sparse bm25)."""
    try:
        info = client.get_collection(name)
        vectors = info.config.params.vectors
        sparse = info.config.params.sparse_vectors or {}
        return isinstance(vectors, dict) and _DENSE in vectors and _SPARSE in sparse
    except Exception:
        return False


def ensure_collections() -> None:
    client = get_qdrant_client()
    for name in [
        settings.QDRANT_COLLECTION_TASKS,
        settings.QDRANT_COLLECTION_KNOWLEDGE,
    ]:
        if client.collection_exists(name) and not _is_hybrid_collection(client, name):
            # Старая dense-only / multi-vector схема несовместима — пересоздаём.
            logger.warning(f"Recreating Qdrant collection with legacy schema: {name}")
            client.delete_collection(name)

        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config={
                    _DENSE: VectorParams(
                        size=settings.EMBEDDINGS_DIM,
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={_SPARSE: SparseVectorParams()},
            )
            logger.info(f"Created Qdrant collection (dense+bm25): {name}")
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
        text = _task_text(clean_title, clean_description)
        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points=[
                PointStruct(
                    id=_task_point_id(task_id),
                    vector={
                        _DENSE: _dense_doc(text),
                        _SPARSE: _sparse_doc(text),
                    },
                    payload={
                        "task_id": task_id,
                        "title": clean_title,
                        "description": clean_description,
                        "team_id": team_id,
                        "text": text,
                    },
                )
            ],
        )
    except Exception as e:
        logger.opt(exception=True).warning(
            "store_task failed (task_id={}): {}", task_id, e
        )


def delete_task(task_id: str) -> None:
    try:
        ids = [_task_point_id(task_id), *_legacy_task_point_ids(task_id)]
        get_qdrant_client().delete(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            points_selector=PointIdsList(points=ids),
        )
        logger.debug("Deleted task {} from Qdrant", task_id)
    except Exception as e:
        logger.opt(exception=True).warning(
            "delete_task failed (task_id={}): {}", task_id, e
        )


def search_tasks(
    query: str,
    team_id: str,
    limit: int = 5,
    score_threshold: float | None = None,
    rerank: bool = True,
) -> list[dict]:
    """Top-N задач команды: hybrid (dense+bm25) + RRF, затем опц. rerank.

    score_threshold применяется к финальному score (relevance_score при rerank).
    rerank=False (напр. голосовой агент) — только hybrid, без сетевого вызова и без
    дефолтного порога.
    """
    try:
        team_filter = Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        )
        points = _hybrid_points(
            settings.QDRANT_COLLECTION_TASKS,
            query,
            team_filter,
            candidates=settings.RERANK_CANDIDATES,
        )
        candidates = [_task_dict(p) for p in points if p.payload]

        if rerank:
            candidates, reranked = _apply_rerank(query, candidates, limit)
        else:
            candidates, reranked = candidates[:limit], False

        if score_threshold is not None:
            threshold = score_threshold
        elif reranked:
            threshold = settings.STATUS_HINT_THRESHOLD
        else:
            threshold = None
        if threshold is not None:
            candidates = [c for c in candidates if c["score"] >= threshold]

        for c in candidates:
            c.pop("_doc", None)
        return candidates[:limit]
    except Exception as e:
        logger.opt(exception=True).warning(
            "search_tasks failed for team {}: {}", team_id, e
        )
        return []


def is_task_duplicate(title: str, description: str, team_id: str) -> bool:
    """Дедуп по dense-косинусу (без реранка): есть ли почти-идентичная задача."""
    try:
        # тот же шаблон, что и при store_task — иначе асимметрия роняет косинус
        query = _task_text(title, description)
        team_filter = Filter(
            must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]
        )
        points = _dense_points(
            settings.QDRANT_COLLECTION_TASKS,
            query,
            team_filter,
            limit=1,
            score_threshold=settings.DEDUP_THRESHOLD,
        )
        if points:
            top = points[0]
            logger.debug(
                "Duplicate found for {!r}: task_id={} score={:.3f}",
                title,
                (top.payload or {}).get("task_id"),
                float(top.score or 0.0),
            )
        return bool(points)
    except Exception as e:
        logger.opt(exception=True).warning(
            "is_task_duplicate failed for {!r}: {}", title, e
        )
        return False


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
        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION_KNOWLEDGE,
            points=[
                PointStruct(
                    id=_knowledge_point_id(source_id),
                    vector={
                        _DENSE: _dense_doc(text),
                        _SPARSE: _sparse_doc(text),
                    },
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
        logger.debug(
            "store_knowledge source_id={} type={} team={}",
            source_id,
            knowledge_type,
            team_id,
        )
    except Exception as e:
        logger.opt(exception=True).warning(
            "store_knowledge failed (source_id={}): {}", source_id, e
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
            "delete_knowledge failed (source_id={}): {}", source_id, e
        )


def _knowledge_filter(
    team_id: str,
    knowledge_type: str | None,
    extra_team_ids: list[str] | None,
) -> Filter:
    if extra_team_ids:
        all_team_ids = [team_id] + list(extra_team_ids)
        min_should = MinShould(
            conditions=[
                FieldCondition(key="team_id", match=MatchValue(value=tid))
                for tid in all_team_ids
            ],
            min_count=1,
        )
        if knowledge_type:
            return Filter(
                must=[FieldCondition(key="type", match=MatchValue(value=knowledge_type))],
                min_should=min_should,
            )
        return Filter(min_should=min_should)

    must = [FieldCondition(key="team_id", match=MatchValue(value=team_id))]
    if knowledge_type:
        must.append(FieldCondition(key="type", match=MatchValue(value=knowledge_type)))
    return Filter(must=must)


def search_knowledge(
    query: str,
    team_id: str,
    knowledge_type: str | None = None,
    limit: int = 3,
    extra_team_ids: list[str] | None = None,
    rerank: bool = True,
) -> list[dict]:
    try:
        normalized = _normalize_text(query)
        if not normalized:
            return []
        query_filter = _knowledge_filter(team_id, knowledge_type, extra_team_ids)
        points = _hybrid_points(
            settings.QDRANT_COLLECTION_KNOWLEDGE,
            normalized,
            query_filter,
            candidates=settings.RERANK_CANDIDATES,
        )
        candidates = [
            {
                "source_id": p.payload.get("source_id", ""),
                "type": p.payload.get("type", ""),
                "title": p.payload.get("title", ""),
                "content": _snippet(p.payload.get("content", "")),
                "score": float(p.score or 0.0),
                "_doc": p.payload.get("content", "") or p.payload.get("title", ""),
            }
            for p in points
            if p.payload
        ]

        if rerank:
            candidates, _ = _apply_rerank(query, candidates, limit)
        else:
            candidates = candidates[:limit]

        for c in candidates:
            c.pop("_doc", None)

        if candidates:
            scores_summary = ", ".join(
                f"{r['type']}:{r['score']:.3f} {r['title'][:30]!r}" for r in candidates
            )
            logger.debug(
                "knowledge search query={!r} team={} extra_teams={} hits=[{}]",
                query[:80],
                team_id,
                extra_team_ids,
                scores_summary,
            )
        else:
            logger.debug(
                "knowledge search query={!r} team={} extra_teams={} hits=[]",
                query[:80],
                team_id,
                extra_team_ids,
            )
        return candidates[:limit]
    except Exception as e:
        logger.opt(exception=True).warning(
            "search_knowledge failed for team {}: {}", team_id, e
        )
        return []
