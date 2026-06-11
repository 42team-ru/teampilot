"""HTTP-клиент к Spring backend для голосовых tools (доска задач).

Аутентификация — заголовок X-Bot-Secret (роль BOT). Без конверта: эндпоинты
возвращают тело DTO напрямую (см. ResponseUtils.ok)."""
from __future__ import annotations

import httpx
from loguru import logger

from settings import settings

_BASE = settings.BACKEND_URL.rstrip("/")
_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}
_TIMEOUT = 12.0


def get_stats(team_id: str) -> dict:
    r = httpx.get(
        f"{_BASE}/tasks/stats",
        params={"teamId": team_id},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def voice_query(
    team_id: str,
    *,
    overdue: bool = False,
    due_before: str | None = None,
    assignee_name: str | None = None,
    column: str | None = None,
    limit: int = 15,
) -> list[dict]:
    params: dict[str, object] = {"teamId": team_id, "overdue": str(overdue).lower(), "limit": limit}
    if due_before:
        params["dueBefore"] = due_before
    if assignee_name:
        params["assigneeName"] = assignee_name
    if column:
        params["column"] = column
    r = httpx.get(
        f"{_BASE}/tasks/voice-query",
        params=params,
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def create_task(
    team_id: str,
    title: str,
    *,
    assignee_name: str | None = None,
    deadline: str | None = None,
    description: str | None = None,
) -> dict:
    body = {
        "teamId": team_id,
        "title": title,
        "assigneeName": assignee_name,
        "deadline": deadline,
        "description": description,
    }
    r = httpx.post(
        f"{_BASE}/tasks/voice-create",
        json=body,
        headers=_HEADERS,
        timeout=_TIMEOUT + 5,
    )
    r.raise_for_status()
    logger.info("voice create_task team={} title={!r}", team_id, title)
    return r.json()
