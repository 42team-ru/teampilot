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
from keyboards.task import build_projects_keyboard
from services.team_service import deactivate_team, get_team_id, update_team_kanban
from services.yougile import YouGileClient
from states.setup import GroupSetupStates
from storage import deactivate_pending_chat, remove_pending_chat, save_pending_chat

router = Router()


@router.message(Command("cancel"), F.chat.type == "private")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.")


class _SetupDeepLink(BaseFilter):
    """Matches /start setup_{chat_id} deep links only."""

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        parts = message.text.split(" ", 1)
        return len(parts) == 2 and parts[1].startswith("setup_")


# ── Helper: send join-link to group ─────────────────────────────────────────

async def _send_join_link_to_group(bot: Bot, chat_id: int, telegram_id: int | None = None) -> None:
    """Fetch teamId and send an invite button to the group."""
    team_id = await get_team_id(chat_id, telegram_id=telegram_id)
    if not team_id:
        logger.warning(f"Could not get teamId for chat {chat_id} after linking")
        return
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
    ]])
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "👋 Бот настроен! Чтобы начать получать задачи — нажмите кнопку ниже:"
            ),
            reply_markup=kb,
        )
    except TelegramForbiddenError:
        logger.warning(f"Cannot send join link to group {chat_id}: bot was removed or no access")


# ── 1. Bot added to group ────────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated, bot: Bot) -> None:
    adder = event.from_user
    chat = event.chat
    chat_title = chat.title or str(chat.id)

    team_id = await get_team_id(chat.id, telegram_id=adder.id)

    if team_id:
        remove_pending_chat(chat.id)
        # Team already linked — just send the invite button
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
        ]])
        try:
            await bot.send_message(
                chat_id=chat.id,
                text=(
                    f"👋 Привет, <b>{chat_title}</b>!\n\n"
                    "Чтобы начать получать задачи — нажмите кнопку ниже:"
                ),
                reply_markup=kb,
            )
        except TelegramForbiddenError:
            pass
        return

    # No team linked yet — ask manager to link via DM
    save_pending_chat(chat.id, chat_title, adder.id)
    group_text = (
        f"👋 Привет! Я добавлен в <b>{chat_title}</b>.\n\n"
        "⚠️ Этот чат ещё не привязан к команде.\n"
        "Менеджер команды должен связать чат через личку бота."
    )
    try:
        await bot.send_message(chat_id=chat.id, text=group_text)
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
                "Нажмите кнопку, чтобы выбрать команду. Также этот чат появится в панели менеджера."
            ),
            reply_markup=kb,
        )
    except TelegramForbiddenError:
        logger.warning(f"Cannot DM adder {adder.id} — no private chat open")


# ── 2. Deep link fallback — /start setup_{chat_id} ──────────────────────────

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

    await state.update_data(pending_chat_id=chat_id, pending_chat_title=chat_title)
    await state.set_state(GroupSetupStates.waiting_for_token)

    await message.answer(
        f"Настройка для группы <b>{chat_title}</b>\n\n"
        "Отправь API токен YouGile:\n"
        "<i>YouGile → Настройки → API → Создать токен</i>"
    )


# ── 3. Receive YouGile token → validate → show board list ───────────────────

@router.message(GroupSetupStates.waiting_for_token)
async def process_yougile_token(message: Message, state: FSMContext) -> None:
    token = (message.text or "").strip()
    if not token:
        await message.answer("Пришли токен YouGile текстом.")
        return

    checking_msg = await message.answer("⏳ Проверяю токен...")

    client = YouGileClient(token)
    is_valid = await client.validate_token()

    if not is_valid:
        await checking_msg.delete()
        await message.answer(
            "❌ Токен не подходит. Проверь и попробуй ещё раз.\n"
            "<i>YouGile → Настройки → API → Создать токен</i>"
        )
        return

    projects = await client.get_projects()

    if not projects:
        await checking_msg.delete()
        await message.answer(
            "⚠️ Нет доступных проектов в этом воркспейсе.\n"
            "Создай хотя бы один проект в YouGile и попробуй снова."
        )
        return

    await state.update_data(
        yougile_token=token,
        pending_projects={p["id"]: p["title"] for p in projects},
    )
    await state.set_state(GroupSetupStates.waiting_for_board_select)

    keyboard = build_projects_keyboard(projects)
    await checking_msg.delete()
    await message.answer(
        "✅ Токен подтверждён! Выбери борд куда создавать задачи:",
        reply_markup=keyboard,
    )


# ── 4. Board selected ────────────────────────────────────────────────────────

@router.callback_query(GroupSetupStates.waiting_for_board_select, F.data.startswith("select_board:"))
async def process_board_selection(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    board_id = callback.data.split(":")[1]

    data = await state.get_data()
    chat_id: int = data["pending_chat_id"]
    chat_title: str = data["pending_chat_title"]
    yougile_token: str = data["yougile_token"]
    projects: dict[str, str] = data.get("pending_projects", {})
    board_title = projects.get(board_id, board_id)

    # Get teamId to update kanban settings
    team_id = await get_team_id(chat_id, telegram_id=callback.from_user.id)
    if team_id:
        ok = await update_team_kanban(team_id, board_id, yougile_token, telegram_id=callback.from_user.id)
        if not ok:
            await callback.message.edit_text(
                "❌ Не удалось сохранить настройки канбана. Попробуй позже."
            )
            await callback.answer()
            return
    else:
        logger.warning(f"No team found for chat {chat_id} during board selection — kanban not saved")

    await state.clear()

    await callback.message.edit_text(
        f"✅ Готово!\n\n"
        f"Группа: <b>{chat_title}</b>\n"
        f"Борд: <b>{board_title}</b>\n\n"
        "Настройка сохранена."
    )

    await _send_join_link_to_group(bot, chat_id, telegram_id=callback.from_user.id)
    await callback.answer()


# ── 5. Bot removed from group ────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_group(event: ChatMemberUpdated) -> None:
    await deactivate_team(event.chat.id)
    deactivate_pending_chat(event.chat.id)
    logger.info(f"Bot removed from group {event.chat.id} ({event.chat.title})")


# ── 6. /setup command in group (admins only) ─────────────────────────────────

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
                f"Настройка группы <b>{message.chat.title}</b>\n\n"
                "Отправь API токен YouGile:\n"
                "<i>YouGile → Настройки → API → Создать токен</i>"
            ),
        )
        await state.set_state(GroupSetupStates.waiting_for_token)
    except TelegramForbiddenError:
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=setup_{message.chat.id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚙️ Открыть настройку", url=deep_link)
        ]])
        await message.answer("Нажми для настройки:", reply_markup=kb)
