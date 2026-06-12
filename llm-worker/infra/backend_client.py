"""HTTP-клиент к Spring backend для голосовых tools (доска задач).

Аутентификация — заголовок X-Bot-Secret (роль BOT). Без конверта: эндпоинты
возвращают тело DTO напрямую (см. ResponseUtils.ok)."""
from __future__ import annotations

import httpx

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


def list_team_members(team_id: str) -> list[dict]:
    """Участники команды [{id, name}] — id передавать в assignee_id. GET /tasks/voice-members."""
    r = httpx.get(
        f"{_BASE}/tasks/voice-members",
        params={"teamId": team_id},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def list_columns(team_id: str) -> list[str]:
    """Названия колонок доски команды. GET /tasks/voice-columns."""
    r = httpx.get(
        f"{_BASE}/tasks/voice-columns",
        params={"teamId": team_id},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def get_context(team_id: str) -> dict:
    """Единый контекст доски за один запрос: {members:[{id,name}], columns:[...], stats:{...}}.
    GET /tasks/voice-context."""
    r = httpx.get(
        f"{_BASE}/tasks/voice-context",
        params={"teamId": team_id},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()
