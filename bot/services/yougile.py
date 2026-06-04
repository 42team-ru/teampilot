from __future__ import annotations

from loguru import logger

from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error


class YouGileClient:
    BASE_URL = "https://ru.yougile.com/api-v2"

    def __init__(self, token: str) -> None:
        self.token = token
        self._headers = {"Authorization": f"Bearer {token}"}

    async def validate_token(self) -> bool:
        """GET /projects - returns True if token is valid."""
        path = "/projects"
        context = {"operation": "validate_token"}
        try:
            resp = await http_client.get(
                f"{self.BASE_URL}{path}",
                headers=self._headers,
            )
        except HttpRequestError as e:
            log_http_request_error(service="YouGile", method="GET", path=path, error=e, context=context)
            return False

        if resp.status_code != 200:
            log_http_response_error(
                resp,
                service="YouGile",
                method="GET",
                path=path,
                expected="200",
                context=context,
            )
            return False

        return True

    async def get_projects(self) -> list[dict]:
        """GET /projects - returns [{"id": str, "title": str}, ...]."""
        path = "/projects"
        context = {"operation": "get_projects"}
        try:
            resp = await http_client.get(
                f"{self.BASE_URL}{path}",
                headers=self._headers,
            )
        except HttpRequestError as e:
            log_http_request_error(service="YouGile", method="GET", path=path, error=e, context=context)
            return []

        if resp.status_code != 200:
            log_http_response_error(
                resp,
                service="YouGile",
                method="GET",
                path=path,
                expected="200",
                context=context,
            )
            return []

        try:
            data = resp.json()
        except ValueError as e:
            logger.warning(
                "YouGile invalid JSON response: method=GET path={} context={} error_type={} error={!r}",
                path,
                context,
                type(e).__name__,
                e,
            )
            return []

        # API may return {"content": [...]} or a plain list.
        if isinstance(data, dict):
            items = data.get("content", data.get("data", []))
        else:
            items = data if isinstance(data, list) else []

        if not isinstance(items, list):
            logger.warning(
                "YouGile unexpected JSON shape: method=GET path={} context={} items_type={}",
                path,
                context,
                type(items).__name__,
            )
            return []

        return [
            {"id": str(p["id"]), "title": str(p.get("title", p.get("name", "")))}
            for p in items
            if isinstance(p, dict) and "id" in p
        ]
