from __future__ import annotations

import httpx
from loguru import logger

from config import settings

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def get_team_id(chat_id: int) -> str | None:
    """POST /auth/invite {chatId} — returns teamId uuid string, or None if not found."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite",
                headers=_HEADERS,
                json={"chatId": chat_id},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on POST /auth/invite chatId={chat_id}: {e}")
        return None

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on POST /auth/invite chatId={chat_id}")
        return None

    return resp.json().get("teamId")


async def get_my_teams(manager_telegram_id: int) -> list[dict]:
    """GET /teams/my — list of teams where the given user is manager."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/teams/my",
                headers={**_HEADERS, "X-Telegram-Id": str(manager_telegram_id)},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /teams/my manager={manager_telegram_id}: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /teams/my manager={manager_telegram_id}")
        return []

    return resp.json()


async def link_chat_to_team(team_id: str, telegram_chat_id: int) -> bool:
    """PATCH /teams/{teamId} body:{telegramChatId} — link a chat to a team. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/teams/{team_id}",
                headers=_HEADERS,
                json={"telegramChatId": telegram_chat_id},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /teams/{team_id}: {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on PATCH /teams/{team_id}")
        return False

    return True


async def update_team_kanban(team_id: str, kanban_id: str, kanban_api_key: str) -> bool:
    """PATCH /teams/{teamId} body:{kanbanId, kanbanApiKey} — update kanban config. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/teams/{team_id}",
                headers=_HEADERS,
                json={"kanbanId": kanban_id, "kanbanApiKey": kanban_api_key},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /teams/{team_id} (kanban update): {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on PATCH /teams/{team_id} (kanban update)")
        return False

    return True


async def deactivate_team(telegram_chat_id: int) -> None:
    """DELETE /teams/{telegramChatId} — mark team inactive."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(
                f"{settings.BACKEND_URL}/teams/{telegram_chat_id}",
                headers=_HEADERS,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on DELETE /teams/{telegram_chat_id}: {e}")
