from __future__ import annotations

import httpx
from loguru import logger

from config import settings


async def register_group(
    chat_id: int,
    chat_title: str,
    added_by_telegram_id: int,
    yougile_token: str,
    yougile_board_id: str,
) -> dict:
    """POST /api/groups — register or re-configure a group."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/api/groups",
                json={
                    "chatId": chat_id,
                    "chatTitle": chat_title,
                    "addedByTelegramId": added_by_telegram_id,
                    "yougileToken": yougile_token,
                    "yougileBoardId": yougile_board_id,
                },
            )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"register_group error for chat {chat_id}: {e}")
        return {}


async def get_group(chat_id: int) -> dict | None:
    """GET /api/groups/{chat_id} — None if not found."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.BACKEND_URL}/api/groups/{chat_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"get_group error for chat {chat_id}: {e}")
        return None


async def is_group_configured(chat_id: int) -> bool:
    return await get_group(chat_id) is not None


async def deactivate_group(chat_id: int) -> None:
    """DELETE /api/groups/{chat_id} — mark group inactive."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(f"{settings.BACKEND_URL}/api/groups/{chat_id}")
    except Exception as e:
        logger.warning(f"deactivate_group error for chat {chat_id}: {e}")
