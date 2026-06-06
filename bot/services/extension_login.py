from __future__ import annotations

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BOT_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def confirm_extension_login(
    *,
    code: str,
    telegram_id: int,
    telegram_login: str | None,
    first_name: str | None,
    last_name: str | None,
) -> bool:
    path = f"/auth/extension-login/{code}/confirm"
    body = {
        "telegramId": telegram_id,
        "telegramLogin": telegram_login,
        "firstName": first_name,
        "lastName": last_name,
    }
    context = {"code": code, "telegram_id": telegram_id}

    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}{path}",
            headers=_BOT_HEADERS,
            json=body,
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        raise BackendApiError.unavailable() from e

    if resp.status_code == 404:
        return False

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
        raise BackendApiError.from_response(resp)

    return True
