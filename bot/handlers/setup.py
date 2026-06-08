from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import BaseFilter, ChatMemberUpdatedFilter, Command, IS_MEMBER, IS_NOT_MEMBER
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from config import settings
from keyboards.task import build_companies_keyboard, build_projects_keyboard
from services.backend_error import BackendApiError
from services.team_service import (
    create_pending_team_chat,
    deactivate_team,
    get_team_id,
    update_team_kanban,
    yougile_auth,
    yougile_select_board,
)
from states.setup import GroupSetupStates

router = Router()

_YOUGILE_CREDENTIALS_RETRY_TEXT = (
    "❌ Не удалось войти в YouGile.\n"
    "Проверь логин и пароль и введи логин ещё раз.\n\n"
    "/cancel — отменить"
)


@router.message(Command("cancel"), F.chat.type == "private")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.")


class _SetupDeepLink(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        parts = message.text.split(" ", 1)
        return len(parts) == 2 and parts[1].startswith("setup_")


# ── Helper ───────────────────────────────────────────────────────────────────

async def _send_join_link_to_group(bot: Bot, chat_id: int, telegram_id: int | None = None) -> None:
    team_id = await get_team_id(chat_id, telegram_id=telegram_id)
    if not team_id:
        return
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
    ]])
    try:
        await bot.send_message(
            chat_id=chat_id,
            text="👋 Бот настроен! Чтобы начать получать задачи — нажмите кнопку ниже:",
            reply_markup=kb,
        )
    except TelegramForbiddenError:
        logger.warning(f"Cannot send join link to group {chat_id}")


async def _ask_for_login(target: Message | CallbackQuery, state: FSMContext, chat_id: int, chat_title: str) -> None:
    await state.update_data(pending_chat_id=chat_id, pending_chat_title=chat_title)
    await state.set_state(GroupSetupStates.waiting_for_login)
    text = (
        f"Подключение YouGile для группы <b>{chat_title}</b>\n\n"
        "Введи <b>логин</b> от YouGile-аккаунта:"
    )
    if isinstance(target, CallbackQuery):
        await target.message.answer(text)
    else:
        await target.answer(text)


# ── 1. Bot added to group ────────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated, bot: Bot) -> None:
    adder = event.from_user
    chat = event.chat
    chat_title = chat.title or str(chat.id)

    team_id = await get_team_id(chat.id, telegram_id=adder.id)

    if team_id:
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
        ]])
        try:
            await bot.send_message(
                chat_id=chat.id,
                text=f"👋 Привет, <b>{chat_title}</b>!\n\nЧтобы начать получать задачи — нажмите кнопку ниже:",
                reply_markup=kb,
            )
        except TelegramForbiddenError:
            pass
        return

    try:
        await create_pending_team_chat(chat.id, chat_title, telegram_id=adder.id)
    except Exception as exc:
        logger.warning(f"Failed to register pending chat {chat.id} (adder {adder.id}): {exc}")

    try:
        await bot.send_message(
            chat_id=chat.id,
            text=(
                f"👋 Привет! Я добавлен в <b>{chat_title}</b>.\n\n"
                "⚠️ Этот чат ещё не привязан к команде.\n"
                "Менеджер команды должен связать чат через личку бота."
            ),
        )
    except TelegramForbiddenError:
        pass

    bot_info = await bot.get_me()
    link_deep_link = f"https://t.me/{bot_info.username}?start=link_{chat.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔗 Привязать чат к команде", url=link_deep_link)
    ]])
    try:
        await bot.send_message(
            chat_id=adder.id,
            text=(
                f"👥 Бот добавлен в <b>{chat_title}</b>.\n\n"
                "Чат ещё не привязан ни к одной команде.\n"
                "Нажмите кнопку, чтобы выбрать команду."
            ),
            reply_markup=kb,
        )
    except TelegramForbiddenError:
        logger.warning(f"Cannot DM adder {adder.id}")


# ── 2. Deep link /start setup_{chat_id} ─────────────────────────────────────

@router.message(_SetupDeepLink())
async def start_with_setup_deep_link(message: Message, state: FSMContext) -> None:
    payload = message.text.split(" ", 1)[1]
    try:
        chat_id = int(payload.replace("setup_", ""))
    except ValueError:
        await message.answer("❌ Неверная ссылка для настройки.")
        return

    try:
        chat = await message.bot.get_chat(chat_id)
        chat_title = chat.title or str(chat_id)
    except Exception:
        chat_title = str(chat_id)

    if settings.MOCK_YOUGILE:
        team_id = await get_team_id(chat_id, telegram_id=message.from_user.id)
        if team_id:
            ok = await update_team_kanban(team_id, settings.MOCK_YOUGILE_BOARD_ID, settings.MOCK_YOUGILE_TOKEN, telegram_id=message.from_user.id)
            logger.info(f"[MOCK] Team {team_id} kanban configured")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
        ])
        await message.answer(f"✅ [MOCK] Группа <b>{chat_title}</b> настроена с mock YouGile.", reply_markup=kb)
        return

    await _ask_for_login(message, state, chat_id, chat_title)


# ── 3. Receive login ─────────────────────────────────────────────────────────

@router.message(GroupSetupStates.waiting_for_login)
async def process_yougile_login(message: Message, state: FSMContext) -> None:
    login = (message.text or "").strip()
    if not login:
        await message.answer("Пришли логин от YouGile текстом.")
        return
    await state.update_data(yougile_login=login)
    await state.set_state(GroupSetupStates.waiting_for_password)
    await message.answer("Теперь введи <b>пароль</b> от YouGile:")


# ── 4. Receive password → call backend ──────────────────────────────────────

@router.message(GroupSetupStates.waiting_for_password)
async def process_yougile_password(message: Message, state: FSMContext) -> None:
    password = (message.text or "").strip()
    if not password:
        await message.answer("Пришли пароль YouGile текстом.")
        return

    # Delete password message so it's not visible in history
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    chat_id: int = data["pending_chat_id"]
    login: str = data["yougile_login"]

    await state.update_data(yougile_password=password)

    checking_msg = await message.answer("⏳ Подключаюсь к YouGile...")

    try:
        result = await yougile_auth(chat_id, login, password, telegram_id=message.from_user.id)
    except BackendApiError as error:
        if _is_yougile_credentials_error(error):
            await _show_yougile_credentials_retry(checking_msg, state)
            return
        raise

    if result is None:
        await checking_msg.edit_text(
            "❌ Не удалось подключиться к YouGile. Проверь логин/пароль и попробуй снова.\n"
            "/cancel — отменить"
        )
        await state.set_state(GroupSetupStates.waiting_for_login)
        return

    await _handle_auth_result(checking_msg, state, result)


# ── 5. Company selected (multiple companies case) ────────────────────────────

@router.callback_query(GroupSetupStates.waiting_for_company_select, F.data.startswith("yougile_company:"))
async def process_company_selection(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = callback.data.split(":")[1]
    data = await state.get_data()
    chat_id: int = data["pending_chat_id"]
    login: str = data["yougile_login"]
    password: str = data["yougile_password"]

    await callback.message.edit_text("⏳ Получаю список досок...")

    try:
        result = await yougile_auth(
            chat_id, login, password,
            company_id=company_id,
            telegram_id=callback.from_user.id,
        )
    except BackendApiError as error:
        if _is_yougile_credentials_error(error):
            await _show_yougile_credentials_retry(callback.message, state)
            await callback.answer()
            return
        raise

    if result is None:
        await callback.message.edit_text("❌ Ошибка подключения. Попробуй /cancel и начни заново.")
        await callback.answer()
        return

    await _handle_auth_result(callback.message, state, result)
    await callback.answer()


# ── 6. Board selected ────────────────────────────────────────────────────────

@router.callback_query(GroupSetupStates.waiting_for_board_select, F.data.startswith("select_board:"))
async def process_board_selection(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    board_id = callback.data.split(":")[1]
    data = await state.get_data()
    chat_id: int = data["pending_chat_id"]
    chat_title: str = data["pending_chat_title"]
    boards: list[dict] = data.get("boards", [])
    board_title = next((b["title"] for b in boards if b["id"] == board_id), board_id)

    ok = await yougile_select_board(chat_id, board_id, telegram_id=callback.from_user.id)
    if not ok:
        await callback.message.edit_text("❌ Не удалось сохранить доску. Попробуй позже.")
        await callback.answer()
        return

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])
    await callback.message.edit_text(
        f"✅ Готово!\n\n"
        f"Группа: <b>{chat_title}</b>\n"
        f"Доска: <b>{board_title}</b>\n\n"
        "Канбан подключён.",
        reply_markup=kb,
    )
    await _send_join_link_to_group(bot, chat_id, telegram_id=callback.from_user.id)
    await callback.answer()


# ── 7. New human member added to a configured group ─────────────────────────
# Uses new_chat_members service message — works without bot being admin.

@router.message(F.new_chat_members, F.chat.type.in_({"group", "supergroup"}))
async def new_members_in_group(message: Message, bot: Bot) -> None:
    team_id = await get_team_id(message.chat.id)
    if not team_id:
        return

    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
    ]])

    for new_member in message.new_chat_members:
        if new_member.is_bot:
            continue
        try:
            await bot.send_message(
                chat_id=new_member.id,
                text=(
                    f"👋 Привет, <b>{new_member.first_name}</b>!\n\n"
                    "Тебя добавили в рабочий чат команды.\n"
                    "Нажми кнопку ниже, чтобы получить доступ к задачам:"
                ),
                reply_markup=kb,
            )
        except TelegramForbiddenError:
            mention = f'<a href="tg://user?id={new_member.id}">{new_member.first_name}</a>'
            try:
                await message.answer(
                    f"👋 {mention}, добро пожаловать в команду!\n\n"
                    "Нажми кнопку ниже, чтобы начать получать задачи:",
                    reply_markup=kb,
                )
            except TelegramForbiddenError:
                logger.warning(f"Cannot send welcome to group {message.chat.id} for new member {new_member.id}")


# ── 8. Bot removed from group ────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_group(event: ChatMemberUpdated) -> None:
    await deactivate_team(event.chat.id, telegram_id=event.from_user.id)
    logger.info(f"Bot removed from group {event.chat.id} ({event.chat.title})")


# ── 9. /setup command in group ───────────────────────────────────────────────

@router.message(Command("setup"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_setup_in_group(message: Message, bot: Bot, state: FSMContext) -> None:
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ("administrator", "creator"):
        await message.answer("⚠️ Только администраторы могут настраивать бота.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    team_id = await get_team_id(message.chat.id, telegram_id=message.from_user.id)
    if not team_id:
        await message.answer(
            "⚠️ Этот чат не привязан к команде.\n"
            "Сначала менеджер команды должен привязать чат через личку бота."
        )
        return

    await state.update_data(
        pending_chat_id=message.chat.id,
        pending_chat_title=message.chat.title,
    )

    if settings.MOCK_YOUGILE:
        ok = await update_team_kanban(team_id, settings.MOCK_YOUGILE_BOARD_ID, settings.MOCK_YOUGILE_TOKEN, telegram_id=message.from_user.id)
        logger.info(f"[MOCK] Team {team_id} kanban reconfigured via /setup")
        try:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=f"✅ [MOCK] Группа <b>{message.chat.title}</b> настроена с mock YouGile.",
            )
        except TelegramForbiddenError:
            await message.answer("✅ [MOCK] Группа настроена.")
        return

    try:
        await bot.send_message(
            chat_id=message.from_user.id,
            text=(
                f"Подключение YouGile для группы <b>{message.chat.title}</b>\n\n"
                "Введи <b>логин</b> от YouGile-аккаунта:"
            ),
        )
        await state.set_state(GroupSetupStates.waiting_for_login)
    except TelegramForbiddenError:
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=setup_{message.chat.id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚙️ Открыть настройку", url=deep_link)
        ]])
        await message.answer("Нажми для настройки в личке:", reply_markup=kb)


# ── Internal helper ──────────────────────────────────────────────────────────

def _is_yougile_credentials_error(error: BackendApiError) -> bool:
    detail = (error.detail or "").lower()
    return (
        error.status == 401 and "yougile" in detail
    ) or (
        error.status == 500
        and "yougile" in detail
        and "401 unauthorized" in detail
    )


async def _show_yougile_credentials_retry(msg: Message, state: FSMContext) -> None:
    await state.update_data(yougile_password=None)
    await state.set_state(GroupSetupStates.waiting_for_login)
    await msg.edit_text(_YOUGILE_CREDENTIALS_RETRY_TEXT)


async def _handle_auth_result(msg: Message, state: FSMContext, result: dict) -> None:
    """Processes YouGileAuthResponse: shows companies or boards."""
    if not result.get("connected"):
        companies = result.get("companies") or []
        if not companies:
            await msg.edit_text("⚠️ Нет доступных компаний YouGile.")
            return
        await state.set_state(GroupSetupStates.waiting_for_company_select)
        await msg.edit_text(
            "В каком воркспейсе работает команда?",
            reply_markup=build_companies_keyboard(companies),
        )
        return

    boards = result.get("boards") or []
    if not boards:
        await msg.edit_text(
            "✅ YouGile подключён, но досок не найдено.\n"
            "Создай доску в YouGile и повтори /setup."
        )
        return

    await state.update_data(boards=boards)
    await state.set_state(GroupSetupStates.waiting_for_board_select)
    await msg.edit_text(
        "✅ Подключено! Выбери доску для задач:",
        reply_markup=build_projects_keyboard(boards),
    )
