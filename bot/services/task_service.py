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


async def get_tasks(
    chat_id: int,
    telegram_id: int | None = None,
    status: str | None = None,
    page: int = 0,
    size: int = 10,
) -> list[dict]:
    """GET /api/tasks?chatId=...&status=...&page=...&size=..."""
    params: dict = {"chatId": chat_id, "page": page, "size": size}
    if status:
        params["status"] = status.upper()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/tasks",
                params=params,
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /api/tasks chatId={chat_id}: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /api/tasks chatId={chat_id}")
        return []

    return resp.json().get("content", [])


async def get_task_by_id(task_id: str, telegram_id: int | None = None) -> dict | None:
    """GET /api/tasks/{id} — None if 404."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/api/tasks/{task_id}",
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /api/tasks/{task_id}: {e}")
        return None

    if resp.status_code == 404:
        return None

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /api/tasks/{task_id}")
        return None

    return resp.json()
