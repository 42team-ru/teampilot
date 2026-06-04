from __future__ import annotations

import httpx
from loguru import logger

from config import settings
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int | None = None) -> dict:
    h = dict(_BASE_HEADERS)
    if telegram_id is not None:
        h["X-Telegram-Id"] = str(telegram_id)
    return h


async def get_team_id(chat_id: int, telegram_id: int | None = None) -> str | None:
    """POST /auth/invite {chatId} - returns teamId, or None if not found."""
    path = "/auth/invite"
    body = {"chatId": chat_id}
    context = {"chat_id": chat_id, "telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        return None

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="POST",
            path=path,
            expected="200 or 404",
            context=context,
            request_json=body,
        )
        return None

    return resp.json().get("teamId")


async def get_my_teams(manager_telegram_id: int) -> list[dict]:
    """GET /teams/my - list teams where the given user is manager."""
    path = "/teams/my"
    context = {"manager_telegram_id": manager_telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(manager_telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="GET", path=path, error=e, context=context)
        return []

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=path,
            expected="200",
            context=context,
        )
        return []

    return resp.json()


async def create_pending_team_chat(
    telegram_chat_id: int,
    chat_title: str,
    telegram_id: int,
) -> dict | None:
    """POST /teams/pending-chats - persist a chat waiting for team link."""
    path = "/teams/pending-chats"
    body = {"telegramChatId": telegram_chat_id, "chatTitle": chat_title}
    context = {
        "telegram_chat_id": telegram_chat_id,
        "chat_title": chat_title,
        "telegram_id": telegram_id,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        return None

    if resp.status_code not in (200, 201):
        log_http_response_error(
            resp,
            service="Backend",
            method="POST",
            path=path,
            expected="200 or 201",
            context=context,
            request_json=body,
        )
        return None

    return resp.json()


async def get_pending_team_chats(manager_telegram_id: int) -> list[dict]:
    """GET /teams/pending-chats - chats added by manager and waiting for link."""
    path = "/teams/pending-chats"
    context = {"manager_telegram_id": manager_telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(manager_telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="GET", path=path, error=e, context=context)
        return []

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=path,
            expected="200",
            context=context,
        )
        return []

    return resp.json()


async def link_chat_to_team(
    team_id: str,
    telegram_chat_id: int,
    telegram_id: int | None = None,
    chat_title: str | None = None,
) -> bool:
    """PATCH /teams/{teamId} body:{telegramChatId} - link a chat to a team."""
    body = {"telegramChatId": telegram_chat_id}
    if chat_title is not None:
        body["chatTitle"] = chat_title

    path = f"/teams/{team_id}"
    context = {
        "team_id": team_id,
        "telegram_chat_id": telegram_chat_id,
        "telegram_id": telegram_id,
        "chat_title": chat_title,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="PATCH",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        return False

    if resp.status_code not in (200, 204):
        log_http_response_error(
            resp,
            service="Backend",
            method="PATCH",
            path=path,
            expected="200 or 204",
            context=context,
            request_json=body,
        )
        return False

    return True


async def update_team_kanban(
    team_id: str,
    kanban_id: str,
    kanban_api_key: str,
    telegram_id: int | None = None,
) -> bool:
    """PATCH /teams/{teamId} body:{kanbanId, kanbanApiKey} - update kanban config."""
    path = f"/teams/{team_id}"
    body = {"kanbanId": kanban_id, "kanbanApiKey": kanban_api_key}
    context = {
        "team_id": team_id,
        "kanban_id": kanban_id,
        "has_kanban_api_key": bool(kanban_api_key),
        "telegram_id": telegram_id,
        "operation": "kanban_update",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="PATCH",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        return False

    if resp.status_code not in (200, 204):
        log_http_response_error(
            resp,
            service="Backend",
            method="PATCH",
            path=path,
            expected="200 or 204",
            context=context,
            request_json=body,
        )
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
    """PATCH /teams/{teamId} - update manager-owned team settings."""
    body: dict = {}
    if telegram_chat_id is not None:
        body["telegramChatId"] = telegram_chat_id
    if chat_title is not None:
        body["chatTitle"] = chat_title
    if kanban_id is not None:
        body["kanbanId"] = kanban_id
    if kanban_api_key is not None:
        body["kanbanApiKey"] = kanban_api_key

    path = f"/teams/{team_id}"
    context = {
        "team_id": team_id,
        "telegram_id": telegram_id,
        "telegram_chat_id": telegram_chat_id,
        "chat_title": chat_title,
        "kanban_id": kanban_id,
        "has_kanban_api_key": kanban_api_key is not None,
        "operation": "manager_update",
    }

    if not body:
        logger.warning("Backend request skipped: method=PATCH path={} reason=empty_update_body context={}", path, context)
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="PATCH",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        return None

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="PATCH",
            path=path,
            expected="200",
            context=context,
            request_json=body,
        )
        return None

    return resp.json()


async def get_team_members(team_id: str, telegram_id: int) -> list[dict]:
    """GET /teams/{teamId}/members - list all members of a team."""
    path = f"/teams/{team_id}/members"
    context = {"team_id": team_id, "telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="GET", path=path, error=e, context=context)
        return []

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=path,
            expected="200",
            context=context,
        )
        return []

    return resp.json()


async def remove_team_member(team_id: str, team_user_id: str, telegram_id: int) -> bool:
    """DELETE /teams/{teamId}/members/{teamUserId} - remove member from team."""
    path = f"/teams/{team_id}/members/{team_user_id}"
    context = {"team_id": team_id, "team_user_id": team_user_id, "telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="DELETE", path=path, error=e, context=context)
        return False

    if resp.status_code not in (200, 204):
        log_http_response_error(
            resp,
            service="Backend",
            method="DELETE",
            path=path,
            expected="200 or 204",
            context=context,
        )
        return False

    return True


async def deactivate_team(telegram_chat_id: int, telegram_id: int | None = None) -> bool:
    """DELETE /teams/{telegramChatId} - mark team inactive."""
    path = f"/teams/{telegram_chat_id}"
    context = {"telegram_chat_id": telegram_chat_id, "telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="DELETE", path=path, error=e, context=context)
        return False

    if resp.status_code not in (200, 204):
        log_http_response_error(
            resp,
            service="Backend",
            method="DELETE",
            path=path,
            expected="200 or 204",
            context=context,
        )
        return False

    return True
