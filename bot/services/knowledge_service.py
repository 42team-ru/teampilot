from __future__ import annotations

from loguru import logger

from config import settings
from services.http_client import HttpRequestError, http_client


async def search_knowledge(query: str, team_id: str, limit: int = 5) -> list[dict]:
    url = f"{settings.LLM_WORKER_URL}/knowledge/search"
    try:
        resp = await http_client.get(url, params={"team_id": team_id, "q": query, "limit": limit})
    except HttpRequestError as e:
        logger.warning("knowledge search request failed: {}", e)
        return []

    if resp.status_code != 200:
        logger.warning("knowledge search returned {}: {}", resp.status_code, resp.text[:200])
        return []

    try:
        return resp.json()
    except Exception as e:
        logger.warning("knowledge search response parse failed: {}", e)
        return []
