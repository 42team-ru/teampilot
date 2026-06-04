from __future__ import annotations

from config import settings
from services.admin_service import clear_user_cache
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int | None = None) -> dict:
    headers = dict(_BASE_HEADERS)
    if telegram_id is not None:
        headers["X-Telegram-Id"] = str(telegram_id)
    return headers


async def register_user(
    *,
    telegram_id: int,
    telegram_login: str | None,
    first_name: str,
    last_name: str,
) -> dict | None:
    """POST /auth/registration - create or refresh a Telegram-linked user."""
    path = "/auth/registration"
    body = {
        "telegramId": telegram_id,
        "telegramLogin": telegram_login,
        "firstName": first_name,
        "lastName": last_name,
    }
    context = {"telegram_id": telegram_id, "telegram_login": telegram_login}

    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
            json=body,
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
            request_json=body,
        )
        raise BackendApiError.unavailable() from e

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
        raise BackendApiError.from_response(resp)

    clear_user_cache(telegram_id)
    return resp.json()


async def update_user(
    *,
    user_id: str,
    telegram_id: int,
    first_name: str,
    last_name: str,
    telegram_login: str | None = None,
) -> dict | None:
    """PATCH /users/{id} - fill missing first/last name and optionally telegramLogin."""
    path = f"/users/{user_id}"
    body: dict = {"firstName": first_name, "lastName": last_name}
    if telegram_login is not None:
        body["telegramLogin"] = telegram_login
    context = {"user_id": user_id, "telegram_id": telegram_id}

    try:
        resp = await http_client.patch(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
            json=body,
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="PATCH",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
            request_json=body,
        )
        raise BackendApiError.unavailable() from e

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="PATCH",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
            request_json=body,
        )
        raise BackendApiError.from_response(resp)

    clear_user_cache(telegram_id)
    return resp.json()


async def patch_telegram_login(
    *,
    user_id: str,
    telegram_id: int,
    telegram_login: str,
) -> None:
    """PATCH /users/{id} - silently write telegramLogin if missing in DB."""
    path = f"/users/{user_id}"
    body = {"telegramLogin": telegram_login}
    context = {"user_id": user_id, "telegram_id": telegram_id}

    try:
        resp = await http_client.patch(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
            json=body,
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="PATCH",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
            request_json=body,
        )
        raise BackendApiError.unavailable() from e

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="PATCH",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
            request_json=body,
        )
        raise BackendApiError.from_response(resp)

    clear_user_cache(telegram_id)
