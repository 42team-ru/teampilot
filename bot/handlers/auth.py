from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from config import settings
from handlers.admin import show_admin_panel
from handlers.member import show_member_panel
from services.admin_service import get_user_by_telegram_id
from services.team_service import get_my_teams, link_chat_to_team, get_team_id
from keyboards.team import build_teams_keyboard
from states.setup import LinkTeamStates
from storage import register_user

router = Router()

_BOT_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


# ── /start join_{teamId} — вступить в команду ────────────────────────────────

async def _handle_join(message: Message, team_id: str) -> None:
    u = message.from_user
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite/{team_id}",
                headers=_BOT_HEADERS,
                json={
                    "telegramId": u.id,
                    "telegramLogin": u.username,
                    "firstName": u.first_name,
                    "lastName": u.last_name,
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        logger.warning(f"Backend unavailable on POST /auth/invite/{team_id}: {e}")
        await message.answer("❌ Бэкенд недоступен, попробуй позже.")
        return

    if resp.status_code == 400:
        await message.answer("❌ Неверный запрос.")
        return
    if resp.status_code != 200:
        await message.answer("❌ Не удалось вступить в команду. Попробуй позже.")
        return

    data = resp.json()
    register_user(u.id, u.username, u.full_name)
    logger.info(f"User {u.id} ({u.full_name}) joined team {team_id}")
    await message.answer(
        f"👋 Добро пожаловать, {u.first_name}! 🎉\n\n"
        "Ты добавлен в команду. Теперь ты будешь получать уведомления о задачах."
    )


# ── /start link_{chatId} — менеджер привязывает чат к команде ────────────────

async def _handle_link(message: Message, state: FSMContext, raw_chat_id: str) -> None:
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await message.answer("❌ Неверная ссылка для привязки.")
        return

    teams = await get_my_teams(message.from_user.id)
    if not teams:
        await message.answer(
            "⚠️ У вас нет команд для привязки.\n"
            "Попросите администратора создать команду через системную панель."
        )
        return

    await state.update_data(pending_link_chat_id=chat_id)
    await state.set_state(LinkTeamStates.waiting_for_team_select)
    await message.answer(
        "🔗 <b>Привязка группового чата к команде</b>\n\n"
        "Выберите команду:",
        reply_markup=build_teams_keyboard(teams),
    )


# ── Callback: выбор команды для привязки ─────────────────────────────────────

@router.callback_query(LinkTeamStates.waiting_for_team_select, F.data.startswith("link_team:"))
async def process_link_team_select(callback, state: FSMContext, bot) -> None:
    team_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    chat_id: int = data["pending_link_chat_id"]
    await state.clear()

    ok = await link_chat_to_team(team_id, chat_id)
    if not ok:
        await callback.message.edit_text("❌ Не удалось привязать чат. Попробуй позже.")
        await callback.answer()
        return

    # Получаем teamId для построения deep-link и отправляем в группу
    resolved_team_id = await get_team_id(chat_id)
    if resolved_team_id:
        bot_info = await bot.get_me()
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        deep_link = f"https://t.me/{bot_info.username}?start=join_{resolved_team_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
        ]])
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ Чат привязан к команде!\n\n"
                    "Чтобы начать получать задачи — нажмите кнопку ниже:"
                ),
                reply_markup=kb,
            )
        except Exception as e:
            logger.warning(f"Cannot send join link to group {chat_id}: {e}")

    await callback.message.edit_text("✅ Чат успешно привязан к команде!")
    await callback.answer()


# ── /start dispatcher ─────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else ""

    # setup_ deep links are intercepted by setup_router (registered first)
    if token.startswith("setup_"):
        return

    if token.startswith("join_"):
        team_id = token[len("join_"):]
        await _handle_join(message, team_id)
        return

    if token.startswith("link_"):
        raw_chat_id = token[len("link_"):]
        await _handle_link(message, state, raw_chat_id)
        return

    # No token — check role via backend
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(
            "У вас нет доступа.\n"
            "Попросите менеджера команды прислать ссылку для вступления."
        )
        return

    role = user.get("systemRole") or user.get("role", "")
    if role == "SYSTEM_ADMIN":
        await show_admin_panel(message)
    else:
        await show_member_panel(message, user)
