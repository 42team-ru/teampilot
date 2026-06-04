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


async def get_team_id(chat_id: int, telegram_id: int | None = None) -> str | None:
    """POST /auth/invite {chatId} — returns teamId uuid string, or None if not found."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite",
                headers=_headers(telegram_id),
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
                headers=_headers(manager_telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /teams/my manager={manager_telegram_id}: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /teams/my manager={manager_telegram_id}")
        return []

    return resp.json()


async def create_pending_team_chat(
    telegram_chat_id: int,
    chat_title: str,
    telegram_id: int,
) -> dict | None:
    """POST /teams/pending-chats — persist a chat where manager added the bot."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/teams/pending-chats",
                headers=_headers(telegram_id),
                json={"telegramChatId": telegram_chat_id, "chatTitle": chat_title},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on POST /teams/pending-chats chatId={telegram_chat_id}: {e}")
        return None

    if resp.status_code not in (200, 201):
        logger.warning(f"Unexpected status {resp.status_code} on POST /teams/pending-chats chatId={telegram_chat_id}")
        return None

    return resp.json()


async def get_pending_team_chats(manager_telegram_id: int) -> list[dict]:
    """GET /teams/pending-chats — chats added by manager and waiting for team link."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/teams/pending-chats",
                headers=_headers(manager_telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /teams/pending-chats manager={manager_telegram_id}: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /teams/pending-chats manager={manager_telegram_id}")
        return []

    return resp.json()


async def link_chat_to_team(
    team_id: str,
    telegram_chat_id: int,
    telegram_id: int | None = None,
    chat_title: str | None = None,
) -> bool:
    """PATCH /teams/{teamId} body:{telegramChatId} — link a chat to a team. Returns True on success."""
    body = {"telegramChatId": telegram_chat_id}
    if chat_title is not None:
        body["chatTitle"] = chat_title

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/teams/{team_id}",
                headers=_headers(telegram_id),
                json=body,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /teams/{team_id}: {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on PATCH /teams/{team_id}")
        return False

    return True


async def update_team_kanban(
    team_id: str,
    kanban_id: str,
    kanban_api_key: str,
    telegram_id: int | None = None,
) -> bool:
    """PATCH /teams/{teamId} body:{kanbanId, kanbanApiKey} — update kanban config. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/teams/{team_id}",
                headers=_headers(telegram_id),
                json={"kanbanId": kanban_id, "kanbanApiKey": kanban_api_key},
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /teams/{team_id} (kanban update): {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on PATCH /teams/{team_id} (kanban update)")
        return False

    return True


async def update_team(
    team_id: str,
    telegram_id: int,
    *,
    telegram_chat_id: int | None = None,
    chat_title: str | None = None,
    kanban_id: str | None = None,
    kanban_api_key: str | None = None,
) -> dict | None:
    """PATCH /teams/{teamId} — update manager-owned team settings."""
    body: dict = {}
    if telegram_chat_id is not None:
        body["telegramChatId"] = telegram_chat_id
    if chat_title is not None:
        body["chatTitle"] = chat_title
    if kanban_id is not None:
        body["kanbanId"] = kanban_id
    if kanban_api_key is not None:
        body["kanbanApiKey"] = kanban_api_key

    if not body:
        logger.warning(f"PATCH /teams/{team_id} skipped: empty update body")
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}/teams/{team_id}",
                headers=_headers(telegram_id),
                json=body,
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on PATCH /teams/{team_id} (manager update): {e}")
        return None

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on PATCH /teams/{team_id} (manager update)")
        return None

    return resp.json()


async def get_team_members(team_id: str, telegram_id: int) -> list[dict]:
    """GET /teams/{teamId}/members — list all members of a team (manager only)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}/teams/{team_id}/members",
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on GET /teams/{team_id}/members: {e}")
        return []

    if resp.status_code != 200:
        logger.warning(f"Unexpected status {resp.status_code} on GET /teams/{team_id}/members")
        return []

    return resp.json()


async def remove_team_member(team_id: str, team_user_id: str, telegram_id: int) -> bool:
    """DELETE /teams/{teamId}/members/{teamUserId} — remove member from team (manager only)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{settings.BACKEND_URL}/teams/{team_id}/members/{team_user_id}",
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on DELETE /teams/{team_id}/members/{team_user_id}: {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on DELETE /teams/{team_id}/members/{team_user_id}")
        return False

    return True


async def deactivate_team(telegram_chat_id: int, telegram_id: int | None = None) -> bool:
    """DELETE /teams/{telegramChatId} — mark team inactive."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{settings.BACKEND_URL}/teams/{telegram_chat_id}",
                headers=_headers(telegram_id),
            )
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(f"Backend unavailable on DELETE /teams/{telegram_chat_id}: {e}")
        return False

    if resp.status_code not in (200, 204):
        logger.warning(f"Unexpected status {resp.status_code} on DELETE /teams/{telegram_chat_id}")
        return False

    return True
