from __future__ import annotations

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpClient, HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int) -> dict[str, str]:
    headers = dict(_BASE_HEADERS)
    headers["X-Telegram-Id"] = str(telegram_id)
    return headers


async def get_user_stats(
    telegram_id: int,
    client: HttpClient = http_client,
) -> dict:
    path = f"/users/{telegram_id}/stats"
    context = {"telegram_id": telegram_id}
    try:
        resp = await client.get(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
        )
    except HttpRequestError as error:
        log_http_request_error(
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            error=error,
            context=context,
        )
        raise BackendApiError.unavailable() from error

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
        )
        raise BackendApiError.from_response(resp)

    return resp.json()
