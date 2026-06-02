from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from loguru import logger

from config import settings
from storage import get_user, register_user, save_yougile_token

router = Router()

YOUGILE_API_URL = "https://ru.yougile.com/api-v2/projects"


class Registration(StatesGroup):
    waiting_yougile_token = State()


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

    # setup_ deep links are handled by setup_router (registered before auth_router)
    if not token or token.startswith("setup_"):
        user = get_user(message.from_user.id)
        if user:
            await message.answer("Вы уже зарегистрированы.")
        else:
            await message.answer("Доступ только по приглашению. Обратитесь к администратору.")
        return

    # Any non-empty payload that is not "setup_" is treated as an invite token
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

    if resp.status_code == 200:
        data = resp.json()
        register_user(u.id, u.username, u.full_name)
        logger.info(f"New user registered: {u.id} ({u.full_name}) via backend invite {token}")

        await message.answer(
            f"Добро пожаловать, {u.first_name}! 🎉\n\n"
            "Теперь привяжи аккаунт YouGile —\n"
            "зайди в YouGile → Настройки → API → скопируй токен и пришли сюда."
        )
        await state.set_state(Registration.waiting_yougile_token)
        return

    logger.warning(f"Unexpected status from /auth/login: {resp.status_code} {resp.text}")
    await message.answer("❌ Бэкенд недоступен, попробуй позже.")


@router.message(Registration.waiting_yougile_token)
async def receive_yougile_token(message: Message, state: FSMContext) -> None:
    token = (message.text or "").strip()
    if not token:
        await message.answer("Пришли токен YouGile текстом.")
        return

    await message.answer("⏳ Проверяю токен...")

    if not await _validate_yougile_token(token):
        await message.answer(
            "❌ Токен не прошёл проверку. Убедись, что скопировал правильно, и попробуй снова."
        )
        return

    save_yougile_token(message.from_user.id, token)
    await state.clear()
    logger.info(f"YouGile token saved for user {message.from_user.id}")

    await message.answer(
        "✅ Аккаунт YouGile привязан!\n"
        "Ты полностью зарегистрирован и можешь работать с ботом."
    )


async def _validate_yougile_token(token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                YOUGILE_API_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"YouGile token validation error: {e}")
        return False
