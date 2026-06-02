from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from loguru import logger

from config import settings
from keyboards.admin import admin_main_keyboard, back_to_admin_keyboard
from services.admin_service import get_team_members, link_user_to_yougile

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
async def admin_invite(callback: CallbackQuery) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite",
                headers={"X-Bot-Secret": settings.BOT_SECRET},
                json={
                    "creatorTelegramId": callback.from_user.id,
                    "createdBy": str(callback.from_user.id),
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        await callback.answer("❌ Бэкенд недоступен", show_alert=True)
        return

    if resp.status_code == 403:
        await callback.answer("⛔ Неверный секрет бота", show_alert=True)
        return

    if resp.status_code == 200:
        invite_url = resp.json()["inviteUrl"]
        await callback.message.edit_text(
            f"📧 <b>Ссылка для приглашения</b>\n\n"
            f"<code>{invite_url}</code>\n\n"
            "Действует 7 дней. Одноразовая.\n"
            "Перешли её участнику — он нажмёт и привяжет свой аккаунт.",
            reply_markup=back_to_admin_keyboard(),
        )
        await callback.answer()
    else:
        await callback.answer("❌ Ошибка сервера", show_alert=True)


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
            "👥 Пока нет зарегистрированных участников.\n"
            "Пригласи команду через «Пригласить участника».",
            reply_markup=back_to_admin_keyboard(),
        )
        await callback.answer()
        return

    lines = ["👥 <b>Команда</b>\n"]
    for m in members:
        icon = "✅" if m.get("yougileLinked") else "⚠️"
        name = m.get("yougileDisplayName") or m.get("telegramLogin") or str(m.get("telegramId", "?"))
        lines.append(f"{icon} {name}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_admin_keyboard(),
    )
    await callback.answer()
