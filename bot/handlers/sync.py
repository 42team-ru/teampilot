from html import escape

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import settings
from keyboards.sync import build_excuse_keyboard
from services import sync_service
from services import sync_state as sync_state_service
from services.http_client import http_client

router = Router()
sync_report_router = Router()


# ---------------------------------------------------------------------------
# Admin test commands
# ---------------------------------------------------------------------------

@router.message(Command("test_sync"))
async def cmd_test_sync(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    await message.answer("⏳ Запускаю вечернюю синхронизацию...")
    await sync_service.trigger_sync()
    await message.answer("✅ Синхронизация запущена — бот отправил промпт во все активные чаты")


@router.message(Command("test_sync_summary"))
async def cmd_test_sync_summary(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    await message.answer("⏳ Закрываю окно синхронизации и отправляю итоги...")
    await sync_service.trigger_summary()
    await message.answer("✅ Summary отправлен менеджерам")


# ---------------------------------------------------------------------------
# Excuse handlers
# ---------------------------------------------------------------------------

async def _submit_excuse(telegram_user_id: int, team_id: str | None, reason: str) -> None:
    await http_client.post(
        f"{settings.BACKEND_URL}/sync/excuse",
        json={"telegramUserId": telegram_user_id, "teamId": team_id, "reason": reason},
        headers={"X-Bot-Secret": settings.BOT_SECRET},
    )


@router.message(Command("excuse"))
async def cmd_excuse(message: Message) -> None:
    text = message.text or ""
    parts = text.split(None, 1)
    reason = parts[1].strip() if len(parts) > 1 else "без объяснений"

    try:
        resp = await http_client.get(
            f"{settings.BACKEND_URL}/sync/excuse/teams",
            params={"telegramUserId": message.from_user.id},
            headers={"X-Bot-Secret": settings.BOT_SECRET},
        )
    except Exception:
        await message.answer("Не удалось получить список команд")
        return

    if resp.status_code != 200:
        await message.answer("Не удалось получить список команд")
        return

    teams = resp.json()
    if not teams:
        await message.answer("Ты не состоишь ни в одной команде.")
        return

    if len(teams) == 1:
        await _submit_excuse(message.from_user.id, teams[0]["teamId"], reason)
        await message.answer(
            f"Понял, тебя не жду на синхронизации сегодня\nКоманда: {escape(teams[0]['teamName'])}",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"В какой команде тебя не ждать?\nПричина: <i>{escape(reason)}</i>",
        reply_markup=build_excuse_keyboard(teams, reason),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("excuse_team:"))
async def excuse_team_selected(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    team_id = parts[1]
    reason = parts[2] if len(parts) > 2 else "без объяснений"
    await _submit_excuse(callback.from_user.id, team_id, reason)
    await callback.message.edit_text(
        f"Понял, тебя не жду на синхронизации сегодня\nПричина: {escape(reason)}",
        reply_markup=None,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("excuse_all:"))
async def excuse_all_teams(callback: CallbackQuery) -> None:
    reason = callback.data.split(":", 1)[1] if ":" in callback.data else "без объяснений"
    await _submit_excuse(callback.from_user.id, None, reason)
    await callback.message.edit_text(
        f"Понял, тебя не жду на синхронизации во всех командах сегодня\nПричина: {escape(reason)}",
        reply_markup=None,
        parse_mode="HTML",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Task approval callbacks
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("sync_task_approve:"))
async def sync_task_approve(callback: CallbackQuery) -> None:
    task_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/approve-task",
            json={"taskId": task_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Задача принята</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("✅ Задача принята")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут принимать задачи", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при одобрении задачи", show_alert=True)


@router.callback_query(F.data.startswith("sync_task_reject:"))
async def sync_task_reject_approval(callback: CallbackQuery) -> None:
    task_id = callback.data.split(":", 1)[1]
    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}/sync/reject-task",
            json={"taskId": task_id, "telegramUserId": callback.from_user.id},
        )
    except Exception:
        await callback.answer("❌ Ошибка соединения", show_alert=True)
        return
    if resp.status_code == 204:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n❌ <b>Задача отклонена</b>",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("Задача отклонена")
    elif resp.status_code == 403:
        await callback.answer("⛔ Только менеджеры могут отклонять задачи", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при отклонении задачи", show_alert=True)


# ---------------------------------------------------------------------------
# Multi-message sync report handler
# ---------------------------------------------------------------------------

class _IsSyncUser(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return (
            message.from_user is not None
            and sync_state_service.is_in_sync(message.from_user.id)
        )


@sync_report_router.message(F.chat.type == "private", _IsSyncUser())
async def handle_sync_report(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if not text:
        await message.answer("Опишите, что вы сделали за день, одним сообщением.")
        return

    sync_state_service.remove_sync_user(user_id)
    resp = await http_client.post(
        f"{settings.BACKEND_URL}/sync/submit",
        json={"telegramUserId": user_id, "text": text},
        headers={"X-Bot-Secret": settings.BOT_SECRET},
    )
    if resp.status_code != 204:
        await message.answer("❌ Ошибка при отправке отчёта.")
    else:
        await message.answer("✅ Отчёт отправлен.")
