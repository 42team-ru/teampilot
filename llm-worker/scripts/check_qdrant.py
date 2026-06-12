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

from infra.qdrant import search_tasks as hybrid_search_tasks
from infra.qdrant import get_qdrant_client
from settings import settings
from qdrant_client.models import Filter, FieldCondition, MatchValue


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
            })

    print(f"\n{'─'*60}")
    print(f"Tasks in Qdrant for team {team_id}: {len(tasks)}")
    print(f"{'─'*60}")
    for t in tasks:
        print(f"  {t['task_id'][:8]}…  {t['title']}")


def search_tasks(team_id: str, query: str, threshold: float):
    print(f"\n{'─'*60}")
    print(f"Query: {query!r}")
    print(f"RERANK_ENABLED = {settings.RERANK_ENABLED}  |  candidates = {settings.RERANK_CANDIDATES}")
    print(f"{'─'*60}")

    hybrid = hybrid_search_tasks(team_id=team_id, query=query, limit=10, rerank=False)
    reranked = hybrid_search_tasks(team_id=team_id, query=query, limit=10, score_threshold=threshold)

    print("HYBRID (dense+bm25 RRF, no rerank):")
    for r in hybrid:
        print(f"  {r['score']:.4f}  {r['task_id'][:8]}…  {r['title']!r}")
    if not hybrid:
        print("  (no results)")

    print(f"\nRERANKED (top, threshold={threshold}):")
    for r in reranked:
        print(f"  {r['score']:.4f}  [{r['matched_kind']}]  {r['task_id'][:8]}…  {r['title']!r}")
    if not reranked:
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
