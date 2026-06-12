"""Cross-encoder reranking via OpenRouter rerank API (Cohere v3.5).

Второй этап RAG-пайплайна: hybrid+RRF даёт ~20 кандидатов (recall),
реранкер пересортировывает их по точной релевантности (precision).
Крутится на стороне OpenRouter → 0 RAM локально.

Грейсфул-деградация: при выключенном флаге, пустом ключе или любой ошибке
возвращаем None — вызывающий код оставляет исходный RRF-порядок.
"""
import functools

import httpx
from loguru import logger

from settings import settings


@functools.lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(timeout=settings.RERANK_TIMEOUT_SECONDS)


def rerank(query: str, documents: list[str], top_n: int) -> list[tuple[int, float]] | None:
    """Вернуть [(исходный_индекс, relevance_score), ...] в порядке убывания.

    None → реранк недоступен/упал, используйте исходный порядок.
    """
    if not settings.RERANK_ENABLED or not settings.RERANK_API_KEY or not documents:
        return None

    try:
        resp = _client().post(
            f"{settings.RERANK_API_BASE}/rerank",
            headers={"Authorization": f"Bearer {settings.RERANK_API_KEY}"},
            json={
                "model": settings.RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": min(top_n, len(documents)),
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        ranked = [
            (int(r["index"]), float(r.get("relevance_score", 0.0)))
            for r in results
            if isinstance(r.get("index"), int) or str(r.get("index", "")).isdigit()
        ]
        if ranked:
            logger.debug(
                "rerank query={!r} docs={} top={:.3f}",
                query[:60],
                len(documents),
                ranked[0][1],
            )
        return ranked or None
    except Exception as e:
        logger.warning("rerank failed (docs={}): {}", len(documents), e)
        return None
