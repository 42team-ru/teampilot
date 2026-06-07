from config import settings
from services.http_client import http_client

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def trigger_sync() -> None:
    await http_client.post(f"{settings.BACKEND_URL}/sync/trigger", headers=_HEADERS)


async def trigger_summary() -> None:
    await http_client.post(f"{settings.BACKEND_URL}/sync/trigger-summary", headers=_HEADERS)


async def trigger_sync_for_chat(chat_id: int, telegram_user_id: int):
    return await http_client.post(
        f"{settings.BACKEND_URL}/sync/trigger-chat",
        json={"chatId": chat_id, "telegramUserId": telegram_user_id},
        headers=_HEADERS,
    )


async def trigger_summary_for_chat(chat_id: int, telegram_user_id: int):
    return await http_client.post(
        f"{settings.BACKEND_URL}/sync/trigger-summary-chat",
        json={"chatId": chat_id, "telegramUserId": telegram_user_id},
        headers=_HEADERS,
    )
