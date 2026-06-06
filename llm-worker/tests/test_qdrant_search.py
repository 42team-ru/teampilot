from types import SimpleNamespace
from uuid import UUID

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


def _point(task_id: str, title: str, kind: str, score: float, description: str = ""):
    return SimpleNamespace(
        score=score,
        payload={
            "task_id": task_id,
            "title": title,
            "description": description,
            "team_id": "team-1",
            "kind": kind,
            "text": f"{kind}: {title} {description}",
        },
    )


def test_store_task_writes_multiple_search_representations(monkeypatch):
    embedder = FakeEmbedder()
    client = FakeClient()
    monkeypatch.setattr(qdrant, "_embedder", lambda: embedder)
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)

    task_id = "11111111-1111-1111-1111-111111111111"
    qdrant.store_task(
        task_id=task_id,
        title="Пересоздать коллекцию Qdrant",
        description="Эмбеддинги поплыли после апдейта.\n\nУверенность ИИ: 91%",
        team_id="team-1",
    )

    points = client.upserts[0]["points"]
    kinds = {point.payload["kind"] for point in points}

    assert kinds == {"summary", "title", "description", "status"}
    assert all(point.payload["task_id"] == task_id for point in points)
    assert all("Уверенность ИИ" not in point.payload["description"] for point in points)
    assert all(UUID(str(point.id)) for point in points)
    assert len(embedder.documents[0]) == 4


def test_search_tasks_aggregates_points_by_task(monkeypatch):
    task_1 = "11111111-1111-1111-1111-111111111111"
    task_2 = "22222222-2222-2222-2222-222222222222"
    client = FakeClient(points=[
        _point(
            task_1,
            "Пересоздать коллекцию Qdrant",
            "title",
            0.74,
            "Эмбеддинги поплыли",
        ),
        _point(
            task_1,
            "Пересоздать коллекцию Qdrant",
            "status",
            0.73,
            "Эмбеддинги поплыли",
        ),
        _point(
            task_2,
            "Написать документацию по REST API",
            "summary",
            0.75,
        ),
    ])
    monkeypatch.setattr(qdrant, "_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)

    result = qdrant.search_tasks("qdrant готов", "team-1", limit=2)

    assert [candidate["task_id"] for candidate in result] == [task_1, task_2]
    assert result[0]["matched_kind"] == "title"
    assert [match["kind"] for match in result[0]["matches"]] == ["title", "status"]
    assert client.query_calls[0]["limit"] >= 2 * len(qdrant._TASK_VECTOR_KINDS)
    assert client.query_calls[0]["score_threshold"] == settings.STATUS_HINT_THRESHOLD


def test_delete_task_removes_old_single_point_and_all_new_representations(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)

    task_id = "11111111-1111-1111-1111-111111111111"
    qdrant.delete_task(task_id)

    point_ids = client.deletes[0]["points_selector"].points

    assert task_id in point_ids
    assert len(point_ids) == 1 + len(qdrant._TASK_VECTOR_KINDS)
    assert all(UUID(point_id) for point_id in point_ids[1:])


def test_duplicate_detection_uses_dedup_threshold(monkeypatch):
    task_id = "11111111-1111-1111-1111-111111111111"
    client = FakeClient(points=[
        _point(task_id, "Пересоздать коллекцию Qdrant", "summary", 0.94),
    ])
    monkeypatch.setattr(qdrant, "_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda: client)

    assert qdrant.is_task_duplicate("Пересоздать коллекцию Qdrant", "", "team-1")
    assert client.query_calls[0]["score_threshold"] == settings.DEDUP_THRESHOLD


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


def test_status_queries_from_batch_use_only_status_like_messages():
    from processor import _status_queries_from_batch

    batch = SimpleNamespace(messages=[
        SimpleNamespace(text="Пошел обедать, вернусь через час"),
        SimpleNamespace(text="Авторизацию закрыл, смотри в мастере"),
        SimpleNamespace(text="ф"),
    ])

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
