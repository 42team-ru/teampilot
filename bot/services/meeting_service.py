from __future__ import annotations

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int) -> dict[str, str]:
    headers = dict(_BASE_HEADERS)
    headers["X-Telegram-Id"] = str(telegram_id)
    return headers


async def create_meeting(
    *,
    team_id: str,
    meeting_url: str,
    telegram_id: int,
) -> dict:
    """POST /meetings - create an active meeting owned by a manager."""
    path = "/meetings"
    body = {
        "teamId": team_id,
        "meetingUrl": meeting_url,
    }
    context = {
        "team_id": team_id,
        "meeting_url": meeting_url,
        "telegram_id": telegram_id,
    }

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

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="POST",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
            request_json=body,
        )
        raise BackendApiError.from_response(resp)

    return resp.json()
