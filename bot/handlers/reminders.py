from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services import notification_settings_service

router = Router()


@router.message(Command("reminders"))
async def cmd_reminders(message: Message) -> None:
    if message.from_user is None:
        return
    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Команда /reminders работает в командном чате.")
        return

    parsed = _parse_reminders_command(message.text or "")
    if parsed is None:
        await message.answer(_usage())
        return

    try:
        if not parsed:
            resp = await notification_settings_service.get_reminder_settings(
                message.chat.id,
                message.from_user.id,
            )
        else:
            resp = await notification_settings_service.update_reminder_settings(
                message.chat.id,
                message.from_user.id,
                **parsed,
            )
    except Exception:
        await message.answer("❌ Не удалось связаться с backend.")
        return

    if resp.status_code == 200:
        await message.answer(_format_settings(resp.json()))
    elif resp.status_code == 403:
        await message.answer("⛔ Настройки напоминаний может менять только менеджер команды")
    elif resp.status_code == 404:
        await message.answer("⚠️ Этот чат не привязан к активной команде")
    elif resp.status_code == 400:
        await message.answer("⚠️ Некорректные значения настроек\n\n" + _usage())
    else:
        await message.answer(f"❌ Backend вернул ошибку {resp.status_code}")


def _parse_reminders_command(text: str) -> dict | None:
    parts = text.split()
    if len(parts) == 1:
        return {}
    command = parts[1].lower()
    try:
        if command == "max" and len(parts) == 3:
            return {"maxRemindersPerTaskPerDay": int(parts[2])}
        if command == "quiet" and len(parts) == 4:
            return {"quietHoursStart": int(parts[2]), "quietHoursEnd": int(parts[3])}
        if command == "stale" and len(parts) == 3:
            return {"staleReminderHours": int(parts[2])}
        if command == "deadline" and len(parts) == 3:
            return {"deadlineReminderMinutesBefore": int(parts[2])}
    except ValueError:
        return None
    return None


def _format_settings(settings: dict) -> str:
    return "\n".join([
        "🔕 <b>Настройки напоминаний</b>",
        "",
        f"Лимит: {settings.get('maxRemindersPerTaskPerDay', 1)} на задачу в день",
        f"Тихие часы: {settings.get('quietHoursStart', 22)}:00-{settings.get('quietHoursEnd', 9)}:00",
        f"Без движения: {settings.get('staleReminderHours', 24)} ч",
        f"До дедлайна: за {settings.get('deadlineReminderMinutesBefore', 120)} мин",
        "",
        escape("/reminders max 1"),
        escape("/reminders quiet 22 9"),
        escape("/reminders stale 24"),
        escape("/reminders deadline 120"),
    ])


def _usage() -> str:
    return "\n".join([
        "Использование:",
        "/reminders",
        "/reminders max 1",
        "/reminders quiet 22 9",
        "/reminders stale 24",
        "/reminders deadline 120",
    ])
