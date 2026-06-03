from __future__ import annotations

import httpx
from loguru import logger

from config import settings

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int | None = None) -> dict:
    h = dict(_BASE_HEADERS)
    if telegram_id is not None:
        h["X-Telegram-Id"] = str(telegram_id)
    return h


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """GET /users/{telegramId} — None if 404."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/users/{telegram_id}",
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /users/{telegram_id}: {e}")
        return None

    if resp.status_code == 404:
        return None

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /users/{telegram_id}")
        return None

    return resp.json()


async def get_team_members(telegram_id: int | None = None) -> list[dict]:
    """GET /users?role=USER"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/users",
                params={"role": "USER"},
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /users?role=USER: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /users?role=USER")
        return []

    return resp.json()


async def create_team(
    chat_title: str,
    admin_telegram_id: int,
    admin_username: str | None,
    kanban_id: str | None = None,
    kanban_api_key: str | None = None,
) -> dict | None:
    """POST /admin/teams — create a team with first manager. Returns TeamResponse or None on error."""
    body: dict = {
        "chatTitle": chat_title,
        "adminTelegramId": admin_telegram_id,
        "adminUsername": admin_username or "",
    }
    if kanban_id:
        body["kanbanId"] = kanban_id
    if kanban_api_key:
        body["kanbanApiKey"] = kanban_api_key

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/admin/teams",
                headers=_headers(admin_telegram_id),
                json=body,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on POST /admin/teams: {e}")
        return None

    if resp.status_code not in (200, 201):
        logger.warning(f"Unexpected status {resp.status_code} on POST /admin/teams: {resp.text}")
        return None

    return resp.json()
