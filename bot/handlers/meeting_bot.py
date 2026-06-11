from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from services.telemost_bot_service import is_session_active, start_session, stop_session

router = Router()

_CB_PILOT = "tmbot:pilot:"         # {meeting_id}
_CB_EXT_CONFIRM = "tmbot:ext_confirm:"  # {meeting_id}
_CB_STOP = "tmbot:stop:"           # {meeting_id}

# meeting_id → {"url": str, "team_id": str}, stored until button is pressed
_pending: dict[str, dict] = {}


def register_pending(meeting_id: str, meeting_url: str, team_id: str = "") -> InlineKeyboardMarkup:
    """Store meeting_url and team_id for later use and return the choice keyboard."""
    _pending[meeting_id] = {"url": meeting_url, "team_id": team_id}
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🤖 Подключить TeamPilot",
            callback_data=f"{_CB_PILOT}{meeting_id}",
        ),
        InlineKeyboardButton(
            text="🖥 Только расширение",
            callback_data=f"{_CB_EXT_CONFIRM}{meeting_id}",
        ),
    ]])


@router.callback_query(F.data.startswith(_CB_PILOT))
async def cb_pilot(call: CallbackQuery) -> None:
    await call.answer()
    meeting_id = call.data[len(_CB_PILOT):]
    pending = _pending.pop(meeting_id, None)

    if pending is None:
        await call.message.edit_text("Сессия устарела. Создайте встречу заново.")
        return

    meeting_url = pending["url"]
    team_id = pending.get("team_id", "")

    await call.message.edit_text("Подключаюсь к звонку...")

    try:
        await start_session(meeting_id=meeting_id, meeting_url=meeting_url, team_id=team_id)
    except Exception as e:
        logger.error("Failed to start Telemost session: {}", e)
        await call.message.edit_text(f"Не удалось запустить бота: {e}")
        return

    stop_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Остановить запись", callback_data=f"{_CB_STOP}{meeting_id}"),
    ]])
    await call.message.edit_text(
        f"<b>TeamPilot подключился к звонку</b>\n\nЗаписываю аудио и создаю задачи автоматически.\n"
        f"Meeting ID: <code>{meeting_id}</code>",
        parse_mode="HTML",
        reply_markup=stop_kb,
    )


@router.callback_query(F.data.startswith(_CB_EXT_CONFIRM))
async def cb_ext_confirm(call: CallbackQuery) -> None:
    await call.answer()
    meeting_id = call.data[len(_CB_EXT_CONFIRM):]
    _pending.pop(meeting_id, None)
    await call.message.edit_text(
        "✅ Встреча создана. Используйте расширение для записи.",
    )


@router.callback_query(F.data.startswith(_CB_STOP))
async def cb_stop_bot(call: CallbackQuery) -> None:
    await call.answer()
    meeting_id = call.data[len(_CB_STOP):]

    if not await is_session_active(meeting_id):
        await call.message.edit_text("Сессия уже остановлена.")
        return

    await stop_session(meeting_id)
    await call.message.edit_text("<b>TeamPilot отключился от звонка.</b>", parse_mode="HTML")
