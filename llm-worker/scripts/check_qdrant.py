"""
Diagnostic script for Qdrant task/knowledge search.

Usage:
  uv run python scripts/check_qdrant.py --team <team_id> --query "Мельник закончил бекенд"
  uv run python scripts/check_qdrant.py --team <team_id> --list-tasks
  uv run python scripts/check_qdrant.py --team <team_id> --query "..." --threshold 0.15
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from infra.qdrant import _embedder, _normalize_text, get_qdrant_client
from settings import settings
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np


def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def list_tasks(team_id: str):
    client = get_qdrant_client()
    results, offset = [], None
    while True:
        batch, offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_TASKS,
            scroll_filter=Filter(must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]),
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        results.extend(batch)
        if offset is None:
            break

    seen = set()
    tasks = []
    for p in results:
        tid = p.payload.get("task_id")
        if tid and tid not in seen:
            seen.add(tid)
            tasks.append({
                "task_id": tid,
                "title": p.payload.get("title", ""),
                "kind": p.payload.get("kind", ""),
            })

    print(f"\n{'─'*60}")
    print(f"Tasks in Qdrant for team {team_id}: {len(tasks)}")
    print(f"{'─'*60}")
    for t in tasks:
        print(f"  [{t['kind']:12s}] {t['task_id'][:8]}…  {t['title']}")


def search_tasks(team_id: str, query: str, threshold: float):
    embedder = _embedder()
    client = get_qdrant_client()
    normalized = _normalize_text(query)
    vector = embedder.embed_query(normalized)

    raw = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_TASKS,
        query=vector,
        limit=20,
        score_threshold=None,
        query_filter=Filter(must=[FieldCondition(key="team_id", match=MatchValue(value=team_id))]),
    )

    print(f"\n{'─'*60}")
    print(f"Query: {query!r}")
    print(f"Normalized: {normalized!r}")
    print(f"STATUS_HINT_THRESHOLD = {settings.STATUS_HINT_THRESHOLD}  |  DEDUP_THRESHOLD = {settings.DEDUP_THRESHOLD}  |  custom = {threshold}")
    print(f"{'─'*60}")

    by_task: dict[str, list] = {}
    for p in raw.points:
        tid = p.payload.get("task_id", "?")
        by_task.setdefault(tid, []).append(p)

    rows = []
    for tid, pts in by_task.items():
        best = max(pts, key=lambda p: p.score)
        title = best.payload.get("title", "")
        rows.append((best.score, tid, title, pts))

    rows.sort(reverse=True)

    for score, tid, title, pts in rows[:10]:
        kinds = {p.payload.get("kind", "?"): f"{p.score:.3f}" for p in pts}
        hit_status = "✅ STATUS" if score >= settings.STATUS_HINT_THRESHOLD else "❌ below status"
        hit_dedup = "✅ DEDUP" if score >= settings.DEDUP_THRESHOLD else ""
        flags = f"{hit_status}  {hit_dedup}".strip()
        print(f"  {score:.4f}  [{flags}]  {tid[:8]}…  {title!r}")
        print(f"           kinds: {kinds}")

    if not rows:
        print("  (no results)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", required=True, help="team_id (UUID)")
    parser.add_argument("--query", default=None, help="Search query text")
    parser.add_argument("--list-tasks", action="store_true", help="List all tasks for team")
    parser.add_argument("--threshold", type=float, default=settings.STATUS_HINT_THRESHOLD, help="Score threshold override")
    args = parser.parse_args()

    if args.list_tasks:
        list_tasks(args.team)

    if args.query:
        search_tasks(args.team, args.query, args.threshold)

    if not args.list_tasks and not args.query:
        parser.print_help()


if __name__ == "__main__":
    main()
