from __future__ import annotations

from dataclasses import dataclass
import time

import httpx

from config import settings
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}
_USER_LOOKUP_TIMEOUT = httpx.Timeout(10.0, connect=3.0)
_USER_CACHE_TTL_SECONDS = 30.0
_USER_MISSING_CACHE_TTL_SECONDS = 5.0
_USER_CACHE: dict[int, tuple[float, dict | None]] = {}


@dataclass(frozen=True)
class UserLookupResult:
    ok: bool
    user: dict | None


def _headers(telegram_id: int | None = None) -> dict:
    h = dict(_BASE_HEADERS)
    if telegram_id is not None:
        h["X-Telegram-Id"] = str(telegram_id)
    return h


async def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """GET /users/{telegramId} - None if 404."""
    result = await lookup_user_by_telegram_id(telegram_id)
    return result.user if result.ok else None


async def lookup_user_by_telegram_id(telegram_id: int) -> UserLookupResult:
    """GET /users/{telegramId}; distinguishes not found from backend failure."""
    cached = _USER_CACHE.get(telegram_id)
    now = time.monotonic()
    if cached is not None:
        expires_at, user = cached
        if expires_at > now:
            return UserLookupResult(ok=True, user=user)
        _USER_CACHE.pop(telegram_id, None)

    path = f"/users/{telegram_id}"
    context = {"telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=_USER_LOOKUP_TIMEOUT) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(service="Backend", method="GET", path=f"{settings.BACKEND_URL}{path}", error=e, context=context)
        return UserLookupResult(ok=False, user=None)

    if resp.status_code == 404:
        _USER_CACHE[telegram_id] = (now + _USER_MISSING_CACHE_TTL_SECONDS, None)
        return UserLookupResult(ok=True, user=None)

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200 or 404",
            context=context,
        )
        return UserLookupResult(ok=False, user=None)

    user = resp.json()
    _USER_CACHE[telegram_id] = (now + _USER_CACHE_TTL_SECONDS, user)
    return UserLookupResult(ok=True, user=user)


def clear_user_cache(telegram_id: int) -> None:
    _USER_CACHE.pop(telegram_id, None)


async def get_team_members(telegram_id: int | None = None) -> list[dict]:
    """GET /users?role=USER."""
    path = "/users"
    params = {"role": "USER"}
    context = {"telegram_id": telegram_id}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.BACKEND_URL}{path}",
                params=params,
                headers=_headers(telegram_id),
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
            params=params,
        )
        return []

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
            params=params,
        )
        return []

    return resp.json()


async def create_team(
    chat_title: str,
    admin_telegram_id: int,
    admin_username: str | None,
    requester_telegram_id: int,
    kanban_id: str | None = None,
    kanban_api_key: str | None = None,
) -> dict | None:
    """POST /admin/teams - create a team with first manager."""
    body: dict = {
        "chatTitle": chat_title,
        "adminTelegramId": admin_telegram_id,
        "adminUsername": admin_username or "",
    }
    if kanban_id:
        body["kanbanId"] = kanban_id
    if kanban_api_key:
        body["kanbanApiKey"] = kanban_api_key

    path = "/admin/teams"
    context = {
        "requester_telegram_id": requester_telegram_id,
        "admin_telegram_id": admin_telegram_id,
        "chat_title": chat_title,
        "has_kanban_id": kanban_id is not None,
        "has_kanban_api_key": kanban_api_key is not None,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}{path}",
                headers=_headers(requester_telegram_id),
                json=body,
            )
    except httpx.RequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=f"{settings.BACKEND_URL}{path}",
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
            path=f"{settings.BACKEND_URL}{path}",
            expected="200 or 201",
            context=context,
            request_json=body,
        )
        return None

    return resp.json()
