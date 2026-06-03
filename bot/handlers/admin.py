from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from config import settings
from keyboards.admin import admin_main_keyboard, back_to_admin_keyboard
from services.admin_service import get_team_members, link_user_to_yougile
from states.invite import InviteCreationStates

router = Router()


# ── Helpers called from auth.py ───────────────────────────────────────────────

async def show_admin_panel(message: Message) -> None:
    await message.answer(
        "👷 <b>Панель администратора</b>\n\nУправляй командой и групповыми чатами:",
        reply_markup=admin_main_keyboard(),
    )


async def show_member_panel(message: Message, user: dict) -> None:
    yougile = user.get("yougileDisplayName")
    if yougile:
        status = f"✅ Привязан к YouGile: <b>{yougile}</b>"
    else:
        status = "⚠️ YouGile аккаунт не привязан"
    await message.answer(
        f"Привет! Ты зарегистрирован в системе.\n\n{status}"
    )


# ── Admin callbacks ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "👷 <b>Панель администратора</b>\n\nУправляй командой и групповыми чатами:",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:invite")
async def admin_invite_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(InviteCreationStates.waiting_for_first_name)
    await callback.message.edit_text(
        "📧 <b>Приглашение участника</b>\n\n"
        "Шаг 1/3 — Введи <b>имя</b> участника:"
    )
    await callback.answer()


@router.message(InviteCreationStates.waiting_for_first_name)
async def invite_first_name(message: Message, state: FSMContext) -> None:
    await state.update_data(invite_first_name=message.text.strip())
    await state.set_state(InviteCreationStates.waiting_for_last_name)
    await message.answer("Шаг 2/3 — Введи <b>фамилию</b>:")


@router.message(InviteCreationStates.waiting_for_last_name)
async def invite_last_name(message: Message, state: FSMContext) -> None:
    await state.update_data(invite_last_name=message.text.strip())
    await state.set_state(InviteCreationStates.waiting_for_position)
    await message.answer("Шаг 3/3 — Введи <b>должность</b> (например: «Backend разработчик»):")


@router.message(InviteCreationStates.waiting_for_position)
async def invite_position(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    first_name = data["invite_first_name"]
    last_name  = data["invite_last_name"]
    position   = message.text.strip()
    await state.clear()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite",
                headers={"X-Bot-Secret": settings.BOT_SECRET},
                json={
                    "creatorTelegramId": message.from_user.id,
                    "createdBy": str(message.from_user.id),
                    "firstName": first_name,
                    "lastName": last_name,
                    "position": position,
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        await message.answer("❌ Бэкенд недоступен, попробуй позже.")
        return

    if resp.status_code == 403:
        await message.answer("⛔ Неверный секрет бота.")
        return

    if resp.status_code == 200:
        invite_url = resp.json()["inviteUrl"]
        await message.answer(
            f"✅ Ссылка для <b>{first_name} {last_name}</b> ({position}):\n\n"
            f"<code>{invite_url}</code>\n\n"
            "Одноразовая. Перешли участнику.",
            reply_markup=back_to_admin_keyboard(),
        )
    else:
        await message.answer("❌ Ошибка сервера.")


@router.callback_query(F.data == "admin:add_to_chat")
async def admin_add_to_chat(callback: CallbackQuery) -> None:
    bot_username = (await callback.bot.get_me()).username
    await callback.message.edit_text(
        f"💬 <b>Как добавить бота в чат</b>\n\n"
        f"1. Открой нужный групповой чат\n"
        f"2. Добавь участника <b>@{bot_username}</b>\n"
        f"3. Бот напишет тебе в личку для настройки YouGile борда\n\n"
        f"<i>Если бот не написал — используй команду /setup в группе (нужны права администратора)</i>",
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:team")
async def admin_team(callback: CallbackQuery) -> None:
    members = await get_team_members()
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
        pos   = m.get("position") or "—"
        tg    = f"@{m['telegramLogin']}" if m.get("telegramLogin") else ""
        yg    = "✅ YouGile" if m.get("yougileLinked") else "⚠️ YouGile не привязан"

        lines.append(f"<b>{name}</b>")
        lines.append(f"  📌 {pos}  {tg}")
        lines.append(f"  {yg}\n")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()
