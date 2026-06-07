from __future__ import annotations

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int | None = None) -> dict:
    h = dict(_BASE_HEADERS)
    if telegram_id is not None:
        h["X-Telegram-Id"] = str(telegram_id)
    return h


async def add_course(team_id: str, url: str, telegram_id: int) -> dict:
    """POST /courses/teams/{teamId}/courses — add course to a team."""
    path = f"/courses/teams/{team_id}/courses"
    body = {"url": url}
    context = {"team_id": team_id, "url": url, "telegram_id": telegram_id}
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

    return resp.json()


async def list_courses(team_id: str, telegram_id: int) -> list[dict]:
    """GET /courses/teams/{teamId}/courses — list courses for a team."""
    path = f"/courses/teams/{team_id}/courses"
    context = {"team_id": team_id, "telegram_id": telegram_id}
    try:
        resp = await http_client.get(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
        )
        raise BackendApiError.unavailable() from e

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
