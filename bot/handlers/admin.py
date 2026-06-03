from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.admin import admin_main_keyboard, back_to_admin_keyboard, skip_keyboard
from services.admin_service import create_team, get_team_members, get_user_by_telegram_id
from states.setup import CreateTeamStates

router = Router()


# ── Helpers called from auth.py ───────────────────────────────────────────────

async def show_admin_panel(message: Message) -> None:
    await message.answer(
        "👷 <b>Панель администратора</b>\n\nУправляй командами и групповыми чатами:",
        reply_markup=admin_main_keyboard(),
    )


# ── /admin command (private chat only) ───────────────────────────────────────

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: Message) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("❌ Пользователь не найден. Сначала вступите в команду.")
        return

    role = user.get("systemRole") or user.get("role", "")
    if role != "SYSTEM_ADMIN":
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    await show_admin_panel(message)


# ── Admin panel callbacks ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "👷 <b>Панель администратора</b>\n\nУправляй командами и групповыми чатами:",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:get_invite")
async def admin_get_invite(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔗 <b>Ссылка для вступления</b>\n\n"
        "Ссылка генерируется автоматически при добавлении бота в групповой чат.\n\n"
        "Чтобы получить ссылку для конкретной группы — добавьте бота в нужный чат, "
        "и он пришлёт кнопку «Вступить в команду» прямо туда.",
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:add_to_chat")
async def admin_add_to_chat(callback: CallbackQuery) -> None:
    bot_username = (await callback.bot.get_me()).username
    await callback.message.edit_text(
        f"💬 <b>Как добавить бота в чат</b>\n\n"
        f"1. Открой нужный групповой чат\n"
        f"2. Добавь участника <b>@{bot_username}</b>\n"
        f"3. Бот пришлёт ссылку для вступления прямо в группу\n\n"
        f"<i>Если чат ещё не привязан к команде — бот попросит менеджера сделать это через личку.</i>",
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:team")
async def admin_team(callback: CallbackQuery) -> None:
    members = await get_team_members(telegram_id=callback.from_user.id)
    if not members:
        await callback.message.edit_text(
            "👥 Пока нет зарегистрированных участников.",
            reply_markup=back_to_admin_keyboard(),
        )
        await callback.answer()
        return

    lines = ["👥 <b>Команда</b>\n"]
    for m in members:
        first = m.get("firstName") or ""
        last  = m.get("lastName") or ""
        name  = f"{first} {last}".strip() or m.get("telegramLogin") or str(m.get("telegramId", "?"))
        tg    = f"@{m['telegramLogin']}" if m.get("telegramLogin") else ""
        lines.append(f"<b>{name}</b>")
        if tg:
            lines.append(f"  {tg}\n")
        else:
            lines.append("")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()


# ── Create Team FSM ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:create_team")
async def admin_create_team_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateTeamStates.waiting_for_chat_title)
    await callback.message.edit_text(
        "🏢 <b>Создание команды</b>\n\n"
        "Шаг 1/3 — Введите <b>название команды</b>:\n"
        "<i>Например: «Backend Team», «Мобильная разработка»</i>"
    )
    await callback.answer()


@router.message(CreateTeamStates.waiting_for_chat_title)
async def create_team_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Введите название команды текстом.")
        return

    await state.update_data(chat_title=title)
    await state.set_state(CreateTeamStates.waiting_for_kanban_id)
    await message.answer(
        f"✅ Название: <b>{title}</b>\n\n"
        "Шаг 2/3 — Введите <b>Kanban ID</b> (YouGile board ID) или пропустите:",
        reply_markup=skip_keyboard("admin:skip_kanban_id"),
    )


@router.callback_query(CreateTeamStates.waiting_for_kanban_id, F.data == "admin:skip_kanban_id")
async def create_team_skip_kanban_id(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(kanban_id=None)
    await state.set_state(CreateTeamStates.waiting_for_kanban_api_key)
    await callback.message.edit_text(
        "Шаг 3/3 — Введите <b>Kanban API Key</b> или пропустите:",
        reply_markup=skip_keyboard("admin:skip_kanban_key"),
    )
    await callback.answer()


@router.message(CreateTeamStates.waiting_for_kanban_id)
async def create_team_kanban_id(message: Message, state: FSMContext) -> None:
    await state.update_data(kanban_id=(message.text or "").strip() or None)
    await state.set_state(CreateTeamStates.waiting_for_kanban_api_key)
    await message.answer(
        "Шаг 3/3 — Введите <b>Kanban API Key</b> или пропустите:",
        reply_markup=skip_keyboard("admin:skip_kanban_key"),
    )


@router.callback_query(CreateTeamStates.waiting_for_kanban_api_key, F.data == "admin:skip_kanban_key")
async def create_team_skip_kanban_key(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(kanban_api_key=None)
    await _finish_create_team(callback.message, state, callback.from_user)
    await callback.answer()


@router.message(CreateTeamStates.waiting_for_kanban_api_key)
async def create_team_kanban_key(message: Message, state: FSMContext) -> None:
    await state.update_data(kanban_api_key=(message.text or "").strip() or None)
    await _finish_create_team(message, state, message.from_user)


async def _finish_create_team(message, state: FSMContext, user) -> None:
    data = await state.get_data()
    await state.clear()

    result = await create_team(
        chat_title=data["chat_title"],
        admin_telegram_id=user.id,
        admin_username=user.username,
        kanban_id=data.get("kanban_id"),
        kanban_api_key=data.get("kanban_api_key"),
    )

    if result is None:
        await message.answer(
            "❌ Не удалось создать команду. Попробуй позже.",
            reply_markup=back_to_admin_keyboard(),
        )
        return

    team_id = result.get("id", "—")
    title = result.get("chatTitle") or data["chat_title"]
    kanban = result.get("kanbanId") or "не указан"

    await message.answer(
        f"✅ <b>Команда создана!</b>\n\n"
        f"📛 Название: <b>{title}</b>\n"
        f"🆔 ID: <code>{team_id}</code>\n"
        f"📋 Kanban: {kanban}\n\n"
        "Добавьте бота в групповой чат и менеджер сможет привязать его к этой команде.",
        reply_markup=back_to_admin_keyboard(),
    )


# ── Cancel FSM ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:cancel_create_team")
async def admin_cancel_create_team(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "👷 <b>Панель администратора</b>\n\nУправляй командами и групповыми чатами:",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()
