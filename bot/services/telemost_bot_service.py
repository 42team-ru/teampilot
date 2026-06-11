from __future__ import annotations

import httpx
from loguru import logger

from config import settings

_TIMEOUT = 10.0


async def start_session(meeting_id: str, meeting_url: str, team_id: str = "") -> None:
    """POST {TELEMOST_BOT_URL}/sessions — start a new Playwright session."""
    url = f"{settings.TELEMOST_BOT_URL}/sessions"
    body = {"meeting_id": meeting_id, "meeting_url": meeting_url, "team_id": team_id}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"telemost-bot returned {resp.status_code}: {resp.text}")
    logger.info("telemost-bot session started: meeting_id={}", meeting_id)


async def stop_session(meeting_id: str) -> None:
    """DELETE {TELEMOST_BOT_URL}/sessions/{meeting_id} — stop a running session."""
    url = f"{settings.TELEMOST_BOT_URL}/sessions/{meeting_id}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(url)
    if resp.status_code not in (200, 204):
        logger.warning("telemost-bot stop returned {}: {}", resp.status_code, resp.text)
    logger.info("telemost-bot session stopped: meeting_id={}", meeting_id)


async def is_session_active(meeting_id: str) -> bool:
    """GET {TELEMOST_BOT_URL}/sessions/{meeting_id} — check whether session is active."""
    url = f"{settings.TELEMOST_BOT_URL}/sessions/{meeting_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json().get("active", False)
        return False
    except Exception as e:
        logger.warning("telemost-bot health check failed for meeting_id={}: {}", meeting_id, e)
        return False
