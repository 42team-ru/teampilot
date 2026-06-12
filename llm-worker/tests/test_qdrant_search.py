from types import SimpleNamespace
from uuid import UUID

import numpy as np

from infra import qdrant
from settings import settings


class FakeEmbedder:
    def __init__(self) -> None:
        self.documents: list[list[str]] = []
        self.queries: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents.append(texts)
        return [[float(i), 0.0] for i, _ in enumerate(texts, start=1)]

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [1.0, 0.0]


class FakeSparse:
    """Имитация fastembed SparseTextEmbedding (passage/query embed)."""

    def _emb(self, texts):
        for _ in texts:
            yield SimpleNamespace(
                indices=np.array([1, 2], dtype=np.int64),
                values=np.array([0.5, 0.6], dtype=np.float32),
            )

    def passage_embed(self, texts):
        return self._emb(texts)

    def query_embed(self, texts):
        return self._emb(texts)


class FakeClient:
    def __init__(self, points: list | None = None) -> None:
        self.points = points or []
        self.upserts: list[dict] = []
        self.deletes: list[dict] = []
        self.query_calls: list[dict] = []

    def upsert(self, **kwargs) -> None:
        self.upserts.append(kwargs)

    def delete(self, **kwargs) -> None:
        self.deletes.append(kwargs)

    def query_points(self, **kwargs):
        self.query_calls.append(kwargs)
        return SimpleNamespace(points=self.points)


def _patch_embedders(monkeypatch, client):
    monkeypatch.setattr(qdrant, "_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(qdrant, "_bm25", lambda: FakeSparse())
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)


def _point(task_id: str, title: str, score: float, description: str = ""):
    return SimpleNamespace(
        score=score,
        payload={
            "task_id": task_id,
            "title": title,
            "description": description,
            "team_id": "team-1",
            "text": f"Задача: {title}. Описание: {description}",
        },
    )


def test_store_task_writes_single_hybrid_point(monkeypatch):
    client = FakeClient()
    _patch_embedders(monkeypatch, client)

    task_id = "11111111-1111-1111-1111-111111111111"
    qdrant.store_task(
        task_id=task_id,
        title="Пересоздать коллекцию Qdrant",
        description="Эмбеддинги поплыли после апдейта.\n\nУверенность ИИ: 91%",
        team_id="team-1",
    )

    points = client.upserts[0]["points"]
    assert len(points) == 1
    point = points[0]
    # один point с двумя именованными векторами
    assert set(point.vector.keys()) == {qdrant._DENSE, qdrant._SPARSE}
    assert point.payload["task_id"] == task_id
    assert "Уверенность ИИ" not in point.payload["description"]
    assert UUID(str(point.id))


def test_search_tasks_uses_hybrid_prefetch_and_rerank(monkeypatch):
    task_1 = "11111111-1111-1111-1111-111111111111"
    task_2 = "22222222-2222-2222-2222-222222222222"
    client = FakeClient(points=[
        _point(task_1, "Пересоздать коллекцию Qdrant", 0.5, "Эмбеддинги поплыли"),
        _point(task_2, "Написать документацию по REST API", 0.33),
    ])
    _patch_embedders(monkeypatch, client)
    # реранк переворачивает порядок: индекс 1 первым
    monkeypatch.setattr(qdrant, "_rerank", lambda q, docs, top_n: [(1, 0.9), (0, 0.4)])

    result = qdrant.search_tasks("qdrant готов", "team-1", limit=2)

    # hybrid: prefetch из dense + bm25, fusion RRF
    call = client.query_calls[0]
    assert len(call["prefetch"]) == 2
    usings = {p.using for p in call["prefetch"]}
    assert usings == {qdrant._DENSE, qdrant._SPARSE}
    # rerank применён: порядок и score из реранкера
    assert [c["task_id"] for c in result] == [task_2, task_1]
    assert result[0]["matched_kind"] == "rerank"
    assert result[0]["score"] == 0.9


def test_search_tasks_without_rerank_keeps_rrf_order(monkeypatch):
    task_1 = "11111111-1111-1111-1111-111111111111"
    task_2 = "22222222-2222-2222-2222-222222222222"
    client = FakeClient(points=[
        _point(task_1, "Задача А", 0.5),
        _point(task_2, "Задача Б", 0.33),
    ])
    _patch_embedders(monkeypatch, client)

    result = qdrant.search_tasks("что-то", "team-1", limit=5, rerank=False)

    assert [c["task_id"] for c in result] == [task_1, task_2]
    assert result[0]["matched_kind"] == "hybrid"


def test_delete_task_removes_main_and_legacy_ids(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)

    task_id = "11111111-1111-1111-1111-111111111111"
    qdrant.delete_task(task_id)

    point_ids = client.deletes[0]["points_selector"].points
    # основной id + legacy (raw + 4 старых kind-представления)
    assert qdrant._task_point_id(task_id) in point_ids
    assert task_id in point_ids
    assert len(point_ids) == 1 + len(qdrant._legacy_task_point_ids(task_id))


def test_duplicate_detection_uses_dense_path_and_threshold(monkeypatch):
    task_id = "11111111-1111-1111-1111-111111111111"
    client = FakeClient(points=[_point(task_id, "Пересоздать коллекцию Qdrant", 0.94)])
    _patch_embedders(monkeypatch, client)

    assert qdrant.is_task_duplicate("Пересоздать коллекцию Qdrant", "", "team-1")
    call = client.query_calls[0]
    # дедуп — чистый dense с косинус-порогом, без prefetch/fusion
    assert call["using"] == qdrant._DENSE
    assert "prefetch" not in call
    assert call["score_threshold"] == settings.DEDUP_THRESHOLD


def test_search_knowledge_includes_extra_team_ids(monkeypatch):
    client = FakeClient(points=[
        SimpleNamespace(
            score=0.91,
            payload={
                "source_id": "course-1",
                "title": "Python",
                "content": "Python basics",
                "team_id": "GLOBAL",
                "type": "course",
            },
        ),
    ])
    _patch_embedders(monkeypatch, client)
    monkeypatch.setattr(qdrant, "_rerank", lambda q, docs, top_n: None)  # фолбэк на RRF-порядок

    result = qdrant.search_knowledge(
        "python",
        "team-1",
        knowledge_type="course",
        extra_team_ids=["GLOBAL"],
        limit=5,
    )

    # фильтр теперь живёт внутри prefetch
    prefetch = client.query_calls[0]["prefetch"]
    query_filter = prefetch[0].filter
    conditions = query_filter.min_should.conditions

    assert [item["source_id"] for item in result] == ["course-1"]
    assert query_filter.min_should.min_count == 1
    assert {condition.match.value for condition in conditions} == {"team-1", "GLOBAL"}
    assert query_filter.must[0].key == "type"
    assert query_filter.must[0].match.value == "course"


def test_format_task_candidates_includes_retrieval_context():
    from processor import format_task_candidates

    text = format_task_candidates([
        {
            "task_id": "11111111-1111-1111-1111-111111111111",
            "title": "Пересоздать коллекцию Qdrant",
            "description": "Эмбеддинги поплыли после апдейта",
            "score": 0.81234,
            "matched_kind": "status",
            "matched_queries": ["qdrant готов"],
        }
    ])

    assert 'task_id: "11111111-1111-1111-1111-111111111111"' in text
    assert 'description: "Эмбеддинги поплыли после апдейта"' in text
    assert "score: 0.812" in text
    assert "matched: status" in text
    assert 'query: "qdrant готов"' in text


def _msg(text: str):
    from datetime import datetime
    return SimpleNamespace(
        text=text,
        message_id="m",
        timestamp=datetime(2026, 6, 12, 10, 0),
        username="user",
        full_name="User",
    )


def test_status_queries_from_batch_use_only_status_like_messages(monkeypatch):
    import processor
    from processor import _status_queries_from_batch

    batch = SimpleNamespace(messages=[
        _msg("Пошел обедать, вернусь через час"),
        _msg("Авторизацию закрыл, смотри в мастере"),
        _msg("ф"),
    ])

    # LLM-экстрактор выделяет только статус-подобные фразы
    monkeypatch.setattr(
        processor,
        "status_query_chain",
        SimpleNamespace(invoke=lambda _: ["Авторизацию закрыл, смотри в мастере"]),
    )

    assert _status_queries_from_batch(batch) == [
        "Авторизацию закрыл, смотри в мастере"
    ]


def test_status_candidate_search_uses_focused_queries(monkeypatch):
    import processor
    from processor import _search_status_task_candidates

    calls = []

    def fake_search_tasks(query: str, team_id: str, limit: int = 5):
        calls.append((query, team_id, limit))
        return [{
            "task_id": "11111111-1111-1111-1111-111111111111",
            "title": "Пересоздать коллекцию Qdrant",
            "score": 0.80,
            "rank_score": 0.83,
            "matched_kind": "status",
        }]

    monkeypatch.setattr(processor, "search_tasks", fake_search_tasks)

    result = _search_status_task_candidates(
        "team-1",
        ["qdrant готов", "авторизацию закрыл"],
        limit=5,
    )

    assert calls == [
        ("qdrant готов", "team-1", 5),
        ("авторизацию закрыл", "team-1", 5),
    ]
    assert result[0]["matched_queries"] == [
        "qdrant готов",
        "авторизацию закрыл",
    ]
