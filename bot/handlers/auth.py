from __future__ import annotations

import httpx
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from loguru import logger

from config import settings
from storage import create_invite, get_invite, get_user, register_user, save_yougile_token, use_invite

router = Router()

YOUGILE_API_URL = "https://ru.yougile.com/api-v2/projects"


class Registration(StatesGroup):
    waiting_yougile_token = State()


@router.message(Command("invite"), F.chat.type == "private")
async def cmd_invite(message: Message) -> None:
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    token = create_invite(message.from_user.id)
    bot_username = (await message.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={token}"

    await message.answer(
        f"✅ Ссылка-приглашение создана:\n{link}\n\n"
        "Ссылка одноразовая — для одного пользователя."
    )
    logger.info(f"Admin {message.from_user.id} created invite {token}")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else ""

    if not token.startswith("inv_"):
        user = get_user(message.from_user.id)
        if user:
            await message.answer("Вы уже зарегистрированы.")
        else:
            await message.answer("Доступ только по приглашению. Обратитесь к администратору.")
        return

    invite = get_invite(token)
    if invite is None:
        await message.answer("❌ Ссылка-приглашение недействительна.")
        return
    if invite.used_by is not None:
        await message.answer("❌ Эта ссылка уже была использована.")
        return
    if get_user(message.from_user.id):
        await message.answer("Вы уже зарегистрированы.")
        return

    u = message.from_user
    register_user(u.id, u.username, u.full_name)
    use_invite(token, u.id)
    logger.info(f"New user registered: {u.id} ({u.full_name}) via invite {token}")

    await message.answer(
        f"Добро пожаловать, {u.first_name}! 🎉\n\n"
        "Теперь привяжи аккаунт YouGile —\n"
        "зайди в YouGile → Настройки → API → скопируй токен и пришли сюда."
    )
    await state.set_state(Registration.waiting_yougile_token)


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
