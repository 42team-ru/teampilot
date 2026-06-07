from config import settings
from services.http_client import http_client

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def get_reminder_settings(chat_id: int, telegram_user_id: int):
    return await http_client.get(
        f"{settings.BACKEND_URL}/notifications/settings",
        params={"chatId": chat_id, "telegramUserId": telegram_user_id},
        headers=_HEADERS,
    )


async def update_reminder_settings(chat_id: int, telegram_user_id: int, **fields):
    payload = {
        "chatId": chat_id,
        "telegramUserId": telegram_user_id,
        **{key: value for key, value in fields.items() if value is not None},
    }
    return await http_client.patch(
        f"{settings.BACKEND_URL}/notifications/settings",
        json=payload,
        headers=_HEADERS,
    )
