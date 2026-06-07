from config import settings
from services.http_client import http_client

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def trigger_sync() -> None:
    await http_client.post(f"{settings.BACKEND_URL}/sync/trigger", headers=_HEADERS)


async def trigger_summary() -> None:
    await http_client.post(f"{settings.BACKEND_URL}/sync/trigger-summary", headers=_HEADERS)
