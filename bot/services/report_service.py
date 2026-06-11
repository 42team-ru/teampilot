from __future__ import annotations

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def get_team_report(team_id: str) -> dict:
    """GET /sync/report?teamId=... - aggregated task stats for a team."""
    path = "/sync/report"
    url = f"{settings.BACKEND_URL}{path}"
    context = {"team_id": team_id}
    try:
        resp = await http_client.get(
            url,
            params={"teamId": team_id},
            headers=_HEADERS,
        )
    except HttpRequestError as e:
        log_http_request_error(service="Backend", method="GET", path=url, error=e, context=context)
        raise BackendApiError.unavailable() from e

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=url,
            expected="200",
            context=context,
        )
        raise BackendApiError.from_response(resp)

    return resp.json()
