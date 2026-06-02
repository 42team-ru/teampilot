from __future__ import annotations

import httpx
from loguru import logger


class YouGileClient:
    BASE_URL = "https://ru.yougile.com/api-v2"

    def __init__(self, token: str) -> None:
        self.token = token
        self._headers = {"Authorization": f"Bearer {token}"}

    async def validate_token(self) -> bool:
        """GET /projects — returns 200 if token is valid."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/projects",
                    headers=self._headers,
                )
            return resp.status_code == 200
        except httpx.TimeoutException:
            logger.warning("YouGile token validation timed out")
            return False
        except Exception as e:
            logger.warning(f"YouGile token validation error: {e}")
            return False

    async def get_projects(self) -> list[dict]:
        """GET /projects — returns [{"id": str, "title": str}, ...]."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/projects",
                    headers=self._headers,
                )
            resp.raise_for_status()
            data = resp.json()
            # API may return {"content": [...]} or a plain list
            if isinstance(data, dict):
                items = data.get("content", data.get("data", []))
            else:
                items = data if isinstance(data, list) else []
            return [
                {"id": str(p["id"]), "title": str(p.get("title", p.get("name", "")))}
                for p in items
                if "id" in p
            ]
        except httpx.TimeoutException:
            logger.warning("YouGile get_projects timed out")
            return []
        except Exception as e:
            logger.warning(f"YouGile get_projects error: {e}")
            return []
