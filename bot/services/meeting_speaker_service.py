from config import settings
from services.http_client import http_client

_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


async def get_speaker_candidates(meeting_id: str, telegram_user_id: int):
    return await http_client.get(
        f"{settings.BACKEND_URL}/meetings/{meeting_id}/speaker-candidates",
        params={"telegramUserId": telegram_user_id},
        headers=_HEADERS,
    )


async def map_speaker(
    meeting_id: str,
    speaker_label: str,
    participant_telegram_id: int | None,
    telegram_user_id: int,
):
    return await http_client.post(
        f"{settings.BACKEND_URL}/meetings/{meeting_id}/speaker-mappings",
        json={
            "speakerLabel": speaker_label,
            "participantTelegramId": participant_telegram_id,
            "telegramUserId": telegram_user_id,
        },
        headers=_HEADERS,
    )
