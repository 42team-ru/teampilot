from __future__ import annotations

import httpx
from loguru import logger

from config import settings

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """GET /api/users/{telegram_id} — None if 404."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/users/{telegram_id}",
                headers=_HEADERS,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /api/users/{telegram_id}: {e}")
        return None

    if resp.status_code == 404:
        return None

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /api/users/{telegram_id}")
        return None

    return resp.json()


async def get_team_members() -> list[dict]:
    """GET /api/users?role=USER"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/users",
                params={"role": "USER"},
                headers=_HEADERS,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /api/users?role=USER: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /api/users?role=USER")
        return []

    return resp.json()


async def link_user_to_yougile(
    telegram_id: int, yougile_user_id: str, yougile_display_name: str
) -> None:
    """PATCH /api/users/{telegram_id}/yougile — body: {yougileUserId, yougileDisplayName}"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/api/users/{telegram_id}/yougile",
                headers=_HEADERS,
                json={
                    "yougileUserId": yougile_user_id,
                    "yougileDisplayName": yougile_display_name,
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /api/users/{telegram_id}/yougile: {e}")
        return

    if resp.status_code not in (200, 204):
        logger.warning(
            f"Unexpected status {resp.status_code} on PATCH /api/users/{telegram_id}/yougile"
        )
