from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.manager import (
    manager_back_keyboard,
    manager_chat_select_keyboard,
    manager_deactivate_confirm_keyboard,
    manager_member_remove_confirm_keyboard,
    manager_members_list_keyboard,
    manager_skip_keyboard,
    manager_team_select_keyboard,
)
from services.team_service import (
    deactivate_team,
    get_my_teams,
    get_pending_team_chats,
    get_team_members,
    link_chat_to_team,
    remove_team_member,
    update_team,
)
from states.manager import ManagerLinkChatStates, ManagerUpdateStates

router = Router()


def _team_title(team: dict) -> str:
    return team.get("chatTitle") or team.get("id") or "Без названия"


def _format_team(team: dict) -> str:
    chat_id = team.get("telegramChatId")
    kanban_id = team.get("kanbanId") or "не указан"
    active = "активна" if team.get("active", True) else "неактивна"
    return (
        f"👥 <b>{_team_title(team)}</b>\n"
        f"ID: <code>{team.get('id', '—')}</code>\n"
        f"Telegram Chat ID: <code>{chat_id if chat_id is not None else 'не привязан'}</code>\n"
        f"Kanban ID: <code>{kanban_id}</code>\n"
        f"Статус: {active}"
    )


async def _get_team_for_manager(telegram_id: int, team_id: str) -> dict | None:
    teams = await get_my_teams(telegram_id)
    return next((team for team in teams if str(team.get("id")) == team_id), None)


async def _send_join_link_to_group(callback: CallbackQuery, chat_id: int, team_id: str) -> None:
    bot_info = await callback.bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=join_{team_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Вступить в команду", url=deep_link)
    ]])
    try:
        await callback.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ Чат привязан к команде!\n\n"
                "Чтобы начать получать задачи — нажмите кнопку ниже:"
            ),
            reply_markup=keyboard,
        )
    except TelegramForbiddenError:
        pass


@router.callback_query(F.data == "manager:members")
async def manager_members_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(members_team_id=None)
    teams = await get_my_teams(callback.from_user.id)
    if not teams:
        await callback.message.edit_text(
            "У вас пока нет команд.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>Участники команды</b>\n\nВыберите команду:",
        reply_markup=manager_team_select_keyboard(teams, "members_list"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:members_list:"))
async def manager_members_list(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    await state.update_data(members_team_id=team_id)

    members = await get_team_members(team_id, callback.from_user.id)
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    team_title = _team_title(team) if team else team_id

    if not members:
        await callback.message.edit_text(
            f"<b>{team_title}</b>\n\nВ команде нет участников.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    lines = [f"<b>Участники: {team_title}</b> ({len(members)})\n"]
    for m in members:
        role_label = "менеджер 🔑" if m.get("role") == "MANAGER" else "участник"
        parts = []
        if m.get("firstName"):
            parts.append(m["firstName"])
        if m.get("lastName"):
            parts.append(m["lastName"])
        name = " ".join(parts) if parts else "Без имени"
        login = m.get("telegramLogin")
        display = f"{name} (@{login})" if login else name
        lines.append(f"• {display} — {role_label}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=manager_members_list_keyboard(members, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:mbr_confirm:"))
async def manager_member_remove_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    team_user_id = callback.data.split(":", 2)[2]
    data = await state.get_data()
    team_id = data.get("members_team_id")

    if not team_id:
        await callback.answer("Сессия истекла, начните заново.", show_alert=True)
        return

    members = await get_team_members(team_id, callback.from_user.id)
    member = next((m for m in members if str(m.get("id")) == team_user_id), None)
    if member is None:
        await callback.message.edit_text(
            "Участник не найден.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    parts = []
    if member.get("firstName"):
        parts.append(member["firstName"])
    if member.get("lastName"):
        parts.append(member["lastName"])
    name = " ".join(parts) if parts else "Без имени"
    login = member.get("telegramLogin")
    display = f"{name} (@{login})" if login else name

    await callback.message.edit_text(
        f"Удалить <b>{display}</b> из команды?",
        reply_markup=manager_member_remove_confirm_keyboard(team_user_id, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:mbr_remove:"))
async def manager_member_remove(callback: CallbackQuery, state: FSMContext) -> None:
    team_user_id = callback.data.split(":", 2)[2]
    data = await state.get_data()
    team_id = data.get("members_team_id")

    if not team_id:
        await callback.answer("Сессия истекла, начните заново.", show_alert=True)
        return

    ok = await remove_team_member(team_id, team_user_id, callback.from_user.id)
    if not ok:
        await callback.message.edit_text(
            "Не удалось удалить участника. Попробуйте позже.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    members = await get_team_members(team_id, callback.from_user.id)
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    team_title = _team_title(team) if team else team_id

    if not members:
        await callback.message.edit_text(
            f"✅ Участник удалён.\n\n<b>{team_title}</b>\n\nВ команде больше нет участников.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    lines = [f"✅ Участник удалён.\n\n<b>Участники: {team_title}</b> ({len(members)})\n"]
    for m in members:
        role_label = "менеджер 🔑" if m.get("role") == "MANAGER" else "участник"
        parts = []
        if m.get("firstName"):
            parts.append(m["firstName"])
        if m.get("lastName"):
            parts.append(m["lastName"])
        name = " ".join(parts) if parts else "Без имени"
        login = m.get("telegramLogin")
        display = f"{name} (@{login})" if login else name
        lines.append(f"• {display} — {role_label}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=manager_members_list_keyboard(members, team_id),
    )
    await callback.answer()


@router.callback_query(F.data == "manager:teams")
async def manager_teams(callback: CallbackQuery) -> None:
    teams = await get_my_teams(callback.from_user.id)
    if not teams:
        await callback.message.edit_text(
            "У вас пока нет команд, где вы указаны менеджером.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    lines = [f"<b>Мои команды</b> ({len(teams)})", ""]
    lines.extend(_format_team(team) for team in teams)
    await callback.message.edit_text(
        "\n\n".join(lines),
        reply_markup=manager_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "manager:link_chat")
async def manager_link_chat_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    chats = await get_pending_team_chats(callback.from_user.id)
    if not chats:
        await callback.message.edit_text(
            "<b>Привязка чата</b>\n\n"
            "Пока нет чатов для привязки.\n\n"
            "Добавьте бота в нужный групповой чат, после этого чат появится здесь кнопкой.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>Привязка чата</b>\n\nВыберите чат, куда вы добавили бота:",
        reply_markup=manager_chat_select_keyboard(chats, "link_chat_select"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:link_chat_select:"))
async def manager_link_chat_select(callback: CallbackQuery, state: FSMContext) -> None:
    raw_chat_id = callback.data.rsplit(":", 1)[1]
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.edit_text(
            "Не удалось определить чат для привязки.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    pending_chats = await get_pending_team_chats(callback.from_user.id)
    pending_chat = next((chat for chat in pending_chats if chat.get("telegramChatId") == chat_id), None)
    if pending_chat is None:
        await callback.message.edit_text(
            "Чат не найден или уже привязан.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    teams = await get_my_teams(callback.from_user.id)
    if not teams:
        await callback.message.edit_text(
            "У вас пока нет команд для привязки.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await state.update_data(
        manager_link_chat_id=chat_id,
        manager_link_chat_title=pending_chat.get("chatTitle") or str(chat_id),
    )
    await state.set_state(ManagerLinkChatStates.waiting_for_team_select)
    await callback.message.edit_text(
        f"<b>Привязка чата</b>\n\n"
        f"Чат: <b>{pending_chat.get('chatTitle') or chat_id}</b>\n\n"
        "Выберите команду:",
        reply_markup=manager_team_select_keyboard(teams, "link_team_select"),
    )
    await callback.answer()


@router.callback_query(ManagerLinkChatStates.waiting_for_team_select, F.data.startswith("manager:link_team_select:"))
async def manager_link_team_select(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.rsplit(":", 1)[1]
    data = await state.get_data()
    await state.clear()

    chat_id = int(data["manager_link_chat_id"])
    chat_title = data.get("manager_link_chat_title") or str(chat_id)
    ok = await link_chat_to_team(team_id, chat_id, telegram_id=callback.from_user.id, chat_title=chat_title)
    if not ok:
        await callback.message.edit_text(
            "Не удалось привязать чат. Попробуйте позже.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await _send_join_link_to_group(callback, chat_id, team_id)
    await callback.message.edit_text(
        f"Чат <b>{chat_title}</b> привязан к команде.",
        reply_markup=manager_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "manager:update")
async def manager_update_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    teams = await get_my_teams(callback.from_user.id)
    if not teams:
        await callback.message.edit_text(
            "У вас пока нет команд для обновления.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>Обновление команды</b>\n\nВыберите команду:",
        reply_markup=manager_team_select_keyboard(teams, "update_select"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:update_select:"))
async def manager_update_select(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.rsplit(":", 1)[1]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас больше нет доступа к ней.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await state.update_data(manager_update_team_id=team_id, manager_update_fields={})
    await state.set_state(ManagerUpdateStates.waiting_for_chat_title)
    await callback.message.edit_text(
        f"<b>Обновление команды</b>\n\n{_format_team(team)}\n\n"
        "Введите новое название команды или пропустите шаг:",
        reply_markup=manager_skip_keyboard("manager:update_skip_chat_title"),
    )
    await callback.answer()


@router.message(ManagerUpdateStates.waiting_for_chat_title)
async def manager_update_chat_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Введите название текстом или нажмите «Пропустить».")
        return

    data = await state.get_data()
    fields = dict(data.get("manager_update_fields", {}))
    fields["chat_title"] = title
    await state.update_data(manager_update_fields=fields)
    await _ask_kanban_id(message, state)


@router.callback_query(ManagerUpdateStates.waiting_for_chat_title, F.data == "manager:update_skip_chat_title")
async def manager_update_skip_chat_title(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_kanban_id(callback.message, state)
    await callback.answer()


async def _ask_kanban_id(message: Message, state: FSMContext) -> None:
    await state.set_state(ManagerUpdateStates.waiting_for_kanban_id)
    await message.answer(
        "Введите новый Kanban ID или пропустите шаг:",
        reply_markup=manager_skip_keyboard("manager:update_skip_kanban_id"),
    )


@router.message(ManagerUpdateStates.waiting_for_kanban_id)
async def manager_update_kanban_id(message: Message, state: FSMContext) -> None:
    kanban_id = (message.text or "").strip()
    if not kanban_id:
        await message.answer("Введите Kanban ID текстом или нажмите «Пропустить».")
        return

    data = await state.get_data()
    fields = dict(data.get("manager_update_fields", {}))
    fields["kanban_id"] = kanban_id
    await state.update_data(manager_update_fields=fields)
    await _ask_kanban_api_key(message, state)


@router.callback_query(ManagerUpdateStates.waiting_for_kanban_id, F.data == "manager:update_skip_kanban_id")
async def manager_update_skip_kanban_id(callback: CallbackQuery, state: FSMContext) -> None:
    await _ask_kanban_api_key(callback.message, state)
    await callback.answer()


async def _ask_kanban_api_key(message: Message, state: FSMContext) -> None:
    await state.set_state(ManagerUpdateStates.waiting_for_kanban_api_key)
    await message.answer(
        "Введите новый Kanban API Key или пропустите шаг:",
        reply_markup=manager_skip_keyboard("manager:update_skip_kanban_api_key"),
    )


@router.message(ManagerUpdateStates.waiting_for_kanban_api_key)
async def manager_update_kanban_api_key(message: Message, state: FSMContext) -> None:
    kanban_api_key = (message.text or "").strip()
    if not kanban_api_key:
        await message.answer("Введите Kanban API Key текстом или нажмите «Пропустить».")
        return

    data = await state.get_data()
    fields = dict(data.get("manager_update_fields", {}))
    fields["kanban_api_key"] = kanban_api_key
    await state.update_data(manager_update_fields=fields)
    await _finish_update(message, state)


@router.callback_query(ManagerUpdateStates.waiting_for_kanban_api_key, F.data == "manager:update_skip_kanban_api_key")
async def manager_update_skip_kanban_api_key(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_update(callback.message, state, telegram_id=callback.from_user.id)
    await callback.answer()


async def _finish_update(message: Message, state: FSMContext, telegram_id: int | None = None) -> None:
    data = await state.get_data()
    await state.clear()

    team_id = data["manager_update_team_id"]
    fields = data.get("manager_update_fields", {})
    if not fields:
        await message.answer(
            "Ничего не изменено.",
            reply_markup=manager_back_keyboard(),
        )
        return

    user_id = telegram_id or message.from_user.id
    updated = await update_team(team_id, user_id, **fields)
    if updated is None:
        await message.answer(
            "Не удалось обновить команду. Попробуйте позже.",
            reply_markup=manager_back_keyboard(),
        )
        return

    await message.answer(
        "<b>Команда обновлена</b>\n\n" + _format_team(updated),
        reply_markup=manager_back_keyboard(),
    )


@router.callback_query(F.data == "manager:update_cancel")
async def manager_update_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Обновление команды отменено.",
        reply_markup=manager_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "manager:deactivate")
async def manager_deactivate_start(callback: CallbackQuery) -> None:
    teams = await get_my_teams(callback.from_user.id)
    if not teams:
        await callback.message.edit_text(
            "У вас пока нет команд для деактивации.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>Деактивация команды</b>\n\nВыберите команду:",
        reply_markup=manager_team_select_keyboard(teams, "deactivate_select"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:deactivate_select:"))
async def manager_deactivate_select(callback: CallbackQuery) -> None:
    team_id = callback.data.rsplit(":", 1)[1]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас больше нет доступа к ней.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    if team.get("telegramChatId") is None:
        await callback.message.edit_text(
            "У команды нет привязанного Telegram Chat ID, поэтому её нельзя деактивировать через эту ручку.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "<b>Подтвердите деактивацию</b>\n\n" + _format_team(team),
        reply_markup=manager_deactivate_confirm_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:deactivate_confirm:"))
async def manager_deactivate_confirm(callback: CallbackQuery) -> None:
    team_id = callback.data.rsplit(":", 1)[1]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас больше нет доступа к ней.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    chat_id = team.get("telegramChatId")
    if chat_id is None:
        await callback.message.edit_text(
            "У команды нет привязанного Telegram Chat ID.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    ok = await deactivate_team(int(chat_id), telegram_id=callback.from_user.id)
    if not ok:
        await callback.message.edit_text(
            "Не удалось деактивировать команду. Попробуйте позже.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Команда <b>{_team_title(team)}</b> деактивирована.",
        reply_markup=manager_back_keyboard(),
    )
    await callback.answer()
