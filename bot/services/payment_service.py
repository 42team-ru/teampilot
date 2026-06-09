from __future__ import annotations

from loguru import logger

from config import settings
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error

_BASE_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


def _headers(telegram_id: int) -> dict:
    return {**_BASE_HEADERS, "X-Telegram-Id": str(telegram_id)}


async def initiate_team_payment(telegram_id: int, team_name: str) -> dict:
    """POST /payments/team → {confirmationUrl, amount, test}"""
    path = "/payments/team"
    body = {"teamName": team_name}
    context = {"telegram_id": telegram_id, "team_name": team_name}
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
            expected="201",
            context=context,
            request_json=body,
        )
        raise BackendApiError.from_response(resp)

    data = resp.json()
    logger.info("Team payment initiated: telegram_id={}, team_name={}, test={}",
                telegram_id, team_name, data.get("test"))
    return data
