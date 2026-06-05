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


async def get_tasks(
    chat_id: int | None = None,
    telegram_id: int | None = None,
    assignee: int | None = None,
    status: str | None = None,
    page: int = 0,
    size: int = 10,
) -> list[dict]:
    """GET /tasks?chatId=...&assignee=...&status=...&page=...&size=..."""
    page_data = await get_tasks_page(
        chat_id=chat_id,
        telegram_id=telegram_id,
        assignee=assignee,
        status=status,
        page=page,
        size=size,
    )
    return page_data.get("content", [])


async def get_tasks_page(
    chat_id: int | None = None,
    telegram_id: int | None = None,
    assignee: int | None = None,
    status: str | None = None,
    page: int = 0,
    size: int = 10,
) -> dict:
    """GET /tasks?chatId=...&assignee=...&status=...&page=...&size=..."""
    path = "/tasks"
    params: dict = {"page": page, "size": size}
    if chat_id is not None:
        params["chatId"] = chat_id
    if assignee is not None:
        params["assignee"] = assignee
    if status:
        params["status"] = status.upper()

    context = {
        "chat_id": chat_id,
        "telegram_id": telegram_id,
        "assignee": assignee,
        "status": status,
        "page": page,
        "size": size,
    }
    try:
        resp = await http_client.get(
            f"{settings.BACKEND_URL}{path}",
            params=params,
            headers=_headers(telegram_id),
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            error=e,
            context=context,
            params=params,
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
            params=params,
        )
        raise BackendApiError.from_response(resp)

    return resp.json()


async def get_task_by_id(task_id: str, telegram_id: int | None = None) -> dict | None:
    """GET /tasks/{id} - None if 404."""
    path = f"/tasks/{task_id}"
    context = {"task_id": task_id, "telegram_id": telegram_id}
    try:
        resp = await http_client.get(
            f"{settings.BACKEND_URL}{path}",
            headers=_headers(telegram_id),
        )
    except HttpRequestError as e:
        log_http_request_error(service="Backend", method="GET", path=f"{settings.BACKEND_URL}{path}", error=e, context=context)
        raise BackendApiError.unavailable() from e

    if resp.status_code == 404:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200",
            context=context,
        )
        raise BackendApiError.from_response(resp)

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="GET",
            path=f"{settings.BACKEND_URL}{path}",
            expected="200 or 404",
            context=context,
        )
        raise BackendApiError.from_response(resp)

    return resp.json()
