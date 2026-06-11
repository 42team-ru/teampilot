from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from loguru import logger

from config import settings
from handlers.member import show_member_panel
from keyboards.member import home_keyboard, mini_app_button
from services.admin_service import get_user_by_telegram_id
from services.backend_error import BackendApiError
from services.http_client import HttpRequestError, http_client
from services.http_logging import log_http_request_error, log_http_response_error
from services.team_service import get_my_teams, link_chat_to_team, get_team_id
from keyboards.team import build_teams_keyboard
from states.auth import JoinTeamStates, RegistrationStates
from states.setup import LinkTeamStates
from storage import register_user

router = Router()

_BOT_HEADERS = {"X-Bot-Secret": settings.BOT_SECRET}


@router.message(Command("app", "miniapp"), F.chat.type == "private")
async def cmd_app(message: Message) -> None:
    await message.answer(
        "Откройте Mini App кнопкой ниже. Так Telegram передаст initData для входа.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[mini_app_button()]]),
    )


# ── /start join_{teamId} — вступить в команду ────────────────────────────────

async def _handle_join(message: Message, team_id: str, state: FSMContext) -> None:
    """Entry point: save team_id and start YouGile credentials FSM."""
    await state.update_data(join_team_id=team_id)
    await state.set_state(JoinTeamStates.waiting_for_yougile_login)
    await message.answer(
        "Для вступления в команду введи <b>логин</b> от YouGile-аккаунта:",
        parse_mode="HTML",
    )


@router.message(JoinTeamStates.waiting_for_yougile_login, F.text)
async def process_join_yougile_login(message: Message, state: FSMContext) -> None:
    login = (message.text or "").strip()
    if not login:
        await message.answer("Пришли логин от YouGile текстом.")
        return
    await state.update_data(join_yougile_login=login)
    await state.set_state(JoinTeamStates.waiting_for_yougile_password)
    await message.answer("Теперь введи <b>пароль</b> от YouGile:", parse_mode="HTML")


@router.message(JoinTeamStates.waiting_for_yougile_password, F.text)
async def process_join_yougile_password(message: Message, state: FSMContext) -> None:
    password = (message.text or "").strip()
    if not password:
        await message.answer("Пришли пароль YouGile текстом.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    team_id: str = data["join_team_id"]
    login: str = data["join_yougile_login"]
    await state.clear()

    u = message.from_user
    path = f"/auth/invite/{team_id}"
    body = {
        "telegramId": u.id,
        "telegramLogin": u.username,
        "firstName": u.first_name,
        "lastName": u.last_name,
        "yougileLogin": login,
        "yougilePassword": password,
    }
    context = {
        "team_id": team_id,
        "telegram_id": u.id,
        "telegram_login": u.username,
    }

    checking_msg = await message.answer("⏳ Подключаюсь...")

    try:
        resp = await http_client.post(
            f"{settings.BACKEND_URL}{path}",
            headers=_BOT_HEADERS,
            json=body,
        )
    except HttpRequestError as e:
        log_http_request_error(
            service="Backend",
            method="POST",
            path=path,
            error=e,
            context=context,
            request_json=body,
        )
        raise BackendApiError.unavailable() from e

    if resp.status_code != 200:
        log_http_response_error(
            resp,
            service="Backend",
            method="POST",
            path=path,
            expected="200",
            context=context,
            request_json=body,
        )
        raise BackendApiError.from_response(resp)

    register_user(u.id, u.username, u.full_name)
    logger.info(f"User {u.id} ({u.full_name}) joined team {team_id}")
    await checking_msg.edit_text(
        f"👋 Добро пожаловать, <b>{u.first_name}</b>! 🎉\n\n"
        "Ты добавлен в команду. Теперь ты будешь получать уведомления о задачах.\n\n"
        "Нажми кнопку, чтобы открыть главное меню:",
        reply_markup=home_keyboard(),
        parse_mode="HTML",
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

    ok = await link_chat_to_team(team_id, chat_id, telegram_id=callback.from_user.id)
    if not ok:
        await callback.message.edit_text("❌ Не удалось привязать чат. Попробуй позже.")
        await callback.answer()
        return

    # Получаем teamId для построения deep-link и отправляем в группу
    resolved_team_id = await get_team_id(chat_id, telegram_id=callback.from_user.id)
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

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])
    await callback.message.edit_text("✅ Чат успешно привязан к команде!", reply_markup=kb)
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
        await _handle_join(message, team_id, state)
        return

    if token.startswith("link_"):
        raw_chat_id = token[len("link_"):]
        await _handle_link(message, state, raw_chat_id)
        return

    # No token — show member/manager panel
    user = await get_user_by_telegram_id(message.from_user.id)
    if user is None:
        await state.update_data(registration_pending_command=message.text)
        await state.set_state(RegistrationStates.waiting_for_first_name)
        await message.answer(
            "Сначала нужно зарегистрироваться.\n"
            "Введите имя. Например: <b>Иван</b>",
            parse_mode="HTML",
        )
        return

    await show_member_panel(message, user)
