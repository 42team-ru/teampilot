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

from keyboards.task import build_projects_keyboard
from services.group_service import deactivate_group, is_group_configured, register_group
from services.yougile import YouGileClient
from states.setup import GroupSetupStates

router = Router()


class _SetupDeepLink(BaseFilter):
    """Matches /start setup_{chat_id} deep links only."""

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        parts = message.text.split(" ", 1)
        return len(parts) == 2 and parts[1].startswith("setup_")


# ── 1. Bot added to group ────────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated, bot: Bot, state: FSMContext) -> None:
    adder = event.from_user
    chat = event.chat

    already_set = await is_group_configured(chat.id)

    if already_set:
        reconfigure_text = (
            f"Я уже настроен в группе <b>{chat.title}</b>.\n\n"
            "Если хочешь переподключить YouGile борд — отправь <b>/setup</b> в группе."
        )
        try:
            await bot.send_message(chat_id=adder.id, text=reconfigure_text)
        except TelegramForbiddenError:
            await bot.send_message(chat_id=chat.id, text=reconfigure_text)
        return

    await state.update_data(pending_chat_id=chat.id, pending_chat_title=chat.title)

    setup_text = (
        f"Привет! Меня добавили в <b>{chat.title}</b> 👷\n\n"
        "Для начала работы отправь мне API токен YouGile:\n"
        "<i>YouGile → Настройки → API → Создать токен</i>"
    )

    try:
        await bot.send_message(chat_id=adder.id, text=setup_text)
        await state.set_state(GroupSetupStates.waiting_for_token)
    except TelegramForbiddenError:
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=setup_{chat.id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚙️ Настроить бота", url=deep_link)
        ]])
        await bot.send_message(
            chat_id=chat.id,
            text=(
                f"Привет! Я готов работать в <b>{chat.title}</b>\n"
                "Для настройки нажми кнопку — нужно открыть личку:"
            ),
            reply_markup=kb,
        )


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
        # Store title map in FSM to avoid 64-byte callback_data limit
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
async def process_board_selection(callback: CallbackQuery, state: FSMContext) -> None:
    board_id = callback.data.split(":")[1]

    data = await state.get_data()
    chat_id: int = data["pending_chat_id"]
    chat_title: str = data["pending_chat_title"]
    yougile_token: str = data["yougile_token"]
    projects: dict[str, str] = data.get("pending_projects", {})
    board_title = projects.get(board_id, board_id)

    await register_group(
        chat_id=chat_id,
        chat_title=chat_title,
        added_by_telegram_id=callback.from_user.id,
        yougile_token=yougile_token,
        yougile_board_id=board_id,
    )

    await state.clear()

    await callback.message.edit_text(
        f"✅ Готово!\n\n"
        f"Группа: <b>{chat_title}</b>\n"
        f"Борд: <b>{board_title}</b>\n\n"
        "Теперь я буду читать переписку и создавать задачи автоматически.\n"
        "Участники команды могут привязать свои аккаунты через /start"
    )

    try:
        await callback.bot.send_message(
            chat_id=chat_id,
            text=(
                f"✅ Настройка завершена! Я буду следить за задачами в этом чате.\n\n"
                f"Борд: <b>{board_title}</b>\n"
                "Каждый участник может привязать свой аккаунт через /start"
            ),
        )
    except TelegramForbiddenError:
        logger.warning(f"Cannot send confirmation to group {chat_id} — bot was removed")

    await callback.answer()


# ── 5. Bot removed from group ────────────────────────────────────────────────

@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_group(event: ChatMemberUpdated) -> None:
    await deactivate_group(event.chat.id)
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
        pass  # not critical if delete fails

    await state.update_data(
        pending_chat_id=message.chat.id,
        pending_chat_title=message.chat.title,
    )

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
