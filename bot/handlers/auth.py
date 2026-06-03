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
from storage import register_user

router = Router()


@router.message(Command("invite"), F.chat.type == "private")
async def cmd_invite(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.BACKEND_URL}/auth/invite",
                headers={"X-Bot-Secret": settings.BOT_SECRET},
                json={
                    "creatorTelegramId": message.from_user.id,
                    "createdBy": str(message.from_user.id),
                },
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        logger.warning(f"Backend unavailable on /invite: {e}")
        await message.answer("❌ Бэкенд недоступен, попробуй позже.")
        return

    if resp.status_code == 403:
        await message.answer("⛔ Неверный секрет бота.")
        return

    if resp.status_code == 200:
        data = resp.json()
        invite_url = data["inviteUrl"]
        await message.answer(
            f"✅ Ссылка-приглашение создана:\n{invite_url}\n\n"
            "Ссылка одноразовая — для одного пользователя."
        )
        logger.info(f"Admin {message.from_user.id} created invite via backend")
        return

    logger.warning(f"Unexpected status from /auth/invite: {resp.status_code} {resp.text}")
    await message.answer("❌ Бэкенд недоступен, попробуй позже.")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else ""

    # setup_ deep links are intercepted by setup_router (registered first)
    if token and not token.startswith("setup_"):
        # Invite token flow
        u = message.from_user
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{settings.BACKEND_URL}/auth/login",
                    json={
                        "inviteToken": token,
                        "telegramId": u.id,
                        "telegramLogin": u.username,
                        "firstName": u.first_name,
                        "lastName": u.last_name,
                    },
                )
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
            logger.warning(f"Backend unavailable on /auth/login: {e}")
            await message.answer("❌ Бэкенд недоступен, попробуй позже.")
            return

        if resp.status_code == 404:
            await message.answer("❌ Ссылка-приглашение недействительна или истекла.")
            return
        if resp.status_code == 400:
            await message.answer("❌ Неверный запрос.")
            return
        if resp.status_code != 200:
            await message.answer("❌ Бэкенд недоступен, попробуй позже.")
            return

        data = resp.json()
        register_user(u.id, u.username, u.full_name)
        logger.info(f"New user registered: {u.id} ({u.full_name})")
        await message.answer(
            f"👋 Добро пожаловать, {u.first_name}! 🎉\n\n"
            "Ты добавлен в команду."
        )
        return

    # No token — check role via backend
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("У вас нет доступа. Запросите инвайт у администратора.")
        return

    role = user.get("role", "")
    if role == "ADMIN":
        await show_admin_panel(message)
    else:
        await show_member_panel(message, user)
