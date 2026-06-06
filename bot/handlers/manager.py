from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from keyboards.manager import (
    back_to_team_ctx_keyboard,
    manager_back_keyboard,
    manager_chat_select_keyboard,
    manager_deactivate_confirm_keyboard,
    manager_member_remove_confirm_keyboard,
    manager_members_list_keyboard,
    manager_skip_keyboard,
    manager_team_select_keyboard,
)
from services.task_service import approve_task, get_task_by_id, get_tasks_page
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

_PENDING_TASKS_PAGE_SIZE = 4
_DISPLAY_TZ = timezone(timedelta(hours=3))


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


def _team_chat_id(team: dict) -> int | None:
    chat_id = team.get("telegramChatId")
    if chat_id is None:
        return None
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return None


def _safe_page(raw_page: str | int | None) -> int:
    try:
        return max(int(raw_page), 0)
    except (TypeError, ValueError):
        return 0


def _total_pages(page_data: dict) -> int:
    return int(page_data.get("totalPages") or 0)


def _total_elements(page_data: dict) -> int:
    return int(page_data.get("totalElements") or len(page_data.get("content", [])))


def _format_deadline(value: str | None) -> str:
    if not value:
        return "не указан"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return escape(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(_DISPLAY_TZ).strftime("%d.%m %H:%M")


def _person_name(info: dict | None, default: str = "не указан") -> str:
    if not info:
        return default
    login = info.get("telegramLogin")
    if login:
        return f"@{escape(str(login))}"
    name = f"{info.get('firstName') or ''} {info.get('lastName') or ''}".strip()
    return escape(name or default)


def _clip(value: str | None, max_length: int = 700) -> str:
    if not value:
        return "—"
    stripped = value.strip()
    if len(stripped) <= max_length:
        return stripped
    return stripped[:max_length - 1].rstrip() + "…"


async def _fetch_pending_tasks_page(
    telegram_id: int,
    team_id: str,
    page: int,
) -> tuple[dict, dict] | None:
    team = await _get_team_for_manager(telegram_id, team_id)
    if team is None:
        return None

    chat_id = _team_chat_id(team)
    if chat_id is None:
        return None

    requested_page = _safe_page(page)
    page_data = await get_tasks_page(
        chat_id=chat_id,
        telegram_id=telegram_id,
        completed=False,
        page=requested_page,
        size=_PENDING_TASKS_PAGE_SIZE,
    )

    total_pages = _total_pages(page_data)
    if requested_page > 0 and total_pages and not page_data.get("content") and requested_page >= total_pages:
        page_data = await get_tasks_page(
            chat_id=chat_id,
            telegram_id=telegram_id,
            completed=False,
            page=total_pages - 1,
            size=_PENDING_TASKS_PAGE_SIZE,
        )

    return team, page_data


def _format_pending_task_row(task: dict, index: int) -> str:
    title = escape(task.get("title") or "Без названия")
    assignee = _person_name(task.get("assignee"), default="без исполнителя")
    deadline = _format_deadline(task.get("deadline"))
    return (
        f"{index}. <b>{title}</b>\n"
        f"   Исполнитель: {assignee}\n"
        f"   Дедлайн: {deadline}"
    )


def _pending_tasks_keyboard(page_data: dict, team_id: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    page = int(page_data.get("page") or 0)
    tasks = page_data.get("content", [])
    start_index = page * int(page_data.get("size") or _PENDING_TASKS_PAGE_SIZE) + 1

    for offset, task in enumerate(tasks):
        task_id = task.get("id")
        if not task_id:
            continue
        index = start_index + offset
        rows.append([
            InlineKeyboardButton(text=f"{index}. 👁 Детали", callback_data=f"mgr:preview:{task_id}"),
            InlineKeyboardButton(text=f"{index}. ✅ Подтвердить", callback_data=f"mgr:approve:{task_id}"),
        ])

    total_pages = _total_pages(page_data)
    if total_pages > 1:
        prev_page = max(page - 1, 0)
        next_page = min(page + 1, total_pages - 1)
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=f"mgr:pending:{team_id}:{prev_page}"),
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"mgr:pending:{team_id}:{page}"),
            InlineKeyboardButton(text="▶️", callback_data=f"mgr:pending:{team_id}:{next_page}"),
        ])

    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"mgr:pending:{team_id}:{page}")])
    rows.append([InlineKeyboardButton(text="← Назад к команде", callback_data=f"team_ctx:manager:{team_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_pending_tasks_page(team: dict, page_data: dict) -> str:
    team_title = escape(_team_title(team))
    tasks = page_data.get("content", [])
    total = _total_elements(page_data)
    page = int(page_data.get("page") or 0)
    total_pages = _total_pages(page_data)

    lines = [
        f"🆕 <b>Новые задачи: {team_title}</b>",
        f"Ожидают подтверждения: <b>{total}</b>",
    ]
    if total_pages:
        lines.append(f"Страница: <b>{page + 1}/{total_pages}</b>")

    if not tasks:
        lines.extend(["", "Новых задач на подтверждение нет."])
    else:
        start_index = page * int(page_data.get("size") or _PENDING_TASKS_PAGE_SIZE) + 1
        lines.append("")
        lines.extend(
            _format_pending_task_row(task, start_index + offset)
            for offset, task in enumerate(tasks)
        )

    return "\n\n".join(lines)


def _format_pending_task_details(task: dict, team: dict) -> str:
    title = escape(task.get("title") or "Без названия")
    description = escape(_clip(task.get("description")))
    return "\n".join([
        "🆕 <b>Задача на подтверждение</b>",
        "",
        f"<b>{title}</b>",
        f"Команда: <b>{escape(_team_title(team))}</b>",
        f"Исполнитель: {_person_name(task.get('assignee'))}",
        f"Автор: {_person_name(task.get('author'))}",
        f"Дедлайн: {_format_deadline(task.get('deadline'))}",
        f"ID: <code>{escape(str(task.get('id') or '—'))}</code>",
        "",
        f"<b>Описание:</b>\n{description}",
    ])


def _pending_task_details_keyboard(task: dict, team_id: str) -> InlineKeyboardMarkup:
    task_id = task.get("id")
    rows: list[list[InlineKeyboardButton]] = []
    if task_id:
        rows.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"mgr:approve:{task_id}")])
    rows.append([InlineKeyboardButton(text="← К новым задачам", callback_data=f"mgr:pending:{team_id}:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("mgr:pending:"))
async def manager_pending_tasks(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Не удалось открыть новые задачи", show_alert=True)
        return

    team_id = parts[2]
    page = _safe_page(parts[3])
    rendered = await _fetch_pending_tasks_page(callback.from_user.id, team_id, page)
    if rendered is None:
        await callback.answer("Команда недоступна или чат не привязан", show_alert=True)
        return

    team, page_data = rendered
    await callback.message.edit_text(
        _format_pending_tasks_page(team, page_data),
        reply_markup=_pending_tasks_keyboard(page_data, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mgr:preview:"))
async def manager_pending_task_preview(callback: CallbackQuery) -> None:
    task_id = (callback.data or "").split(":", 2)[2]
    task = await get_task_by_id(task_id, telegram_id=callback.from_user.id)
    team_id = str(task.get("teamId") or "")
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Задача недоступна", show_alert=True)
        return

    await callback.message.edit_text(
        _format_pending_task_details(task, team),
        reply_markup=_pending_task_details_keyboard(task, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mgr:approve:"))
async def manager_pending_task_approve(callback: CallbackQuery) -> None:
    task_id = (callback.data or "").split(":", 2)[2]
    approved = await approve_task(task_id, callback.from_user.id)
    team_id = str(approved.get("teamId") or "")
    rendered = await _fetch_pending_tasks_page(callback.from_user.id, team_id, 0)
    if rendered is None:
        await callback.message.edit_text(
            "✅ Задача подтверждена.",
            reply_markup=manager_back_keyboard(),
        )
        await callback.answer("Подтверждено")
        return

    team, page_data = rendered
    text = "✅ Задача подтверждена.\n\n" + _format_pending_tasks_page(team, page_data)
    await callback.message.edit_text(
        text,
        reply_markup=_pending_tasks_keyboard(page_data, team_id),
    )
    await callback.answer("Подтверждено")


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
    await _finish_update(message, state)


@router.callback_query(ManagerUpdateStates.waiting_for_chat_title, F.data == "manager:update_skip_chat_title")
async def manager_update_skip_chat_title(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_update(callback.message, state, telegram_id=callback.from_user.id)
    await callback.answer()


async def _finish_update(message: Message, state: FSMContext, telegram_id: int | None = None) -> None:
    data = await state.get_data()
    await state.clear()

    team_id = data["manager_update_team_id"]
    ctx_team_id = data.get("manager_update_ctx_team_id")
    fields = data.get("manager_update_fields", {})
    user_id = telegram_id or message.from_user.id

    if fields:
        updated = await update_team(team_id, user_id, **fields)
        if updated is None:
            kb = back_to_team_ctx_keyboard(team_id) if ctx_team_id else manager_back_keyboard()
            await message.answer(
                "Не удалось обновить команду. Попробуйте позже.",
                reply_markup=kb,
            )
            return
        team = updated
        result_text = "<b>Команда обновлена</b>\n\n" + _format_team(team)
    else:
        teams = await get_my_teams(user_id)
        team = next((t for t in teams if t["id"] == team_id), None)
        result_text = "Название не изменено."

    chat_id = team.get("telegramChatId") if team else None

    if ctx_team_id:
        rows = []
        if chat_id:
            rows.append([InlineKeyboardButton(text="⚙️ Настроить YouGile", callback_data=f"manager:setup_yougile:{chat_id}")])
        rows.append([InlineKeyboardButton(text="← Назад к команде", callback_data=f"team_ctx:manager:{team_id}")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
    else:
        kb = _yougile_setup_keyboard(chat_id) if chat_id else manager_back_keyboard()

    await message.answer(result_text, reply_markup=kb)


def _yougile_setup_keyboard(chat_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настроить YouGile", callback_data=f"manager:setup_yougile:{chat_id}")],
        [InlineKeyboardButton(text="« Назад", callback_data="manager:back")],
    ])


@router.callback_query(F.data.startswith("manager:setup_yougile:"))
async def manager_setup_yougile(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_title = chat.title or str(chat_id)
    except Exception:
        chat_title = str(chat_id)

    from states.setup import GroupSetupStates
    await state.update_data(pending_chat_id=chat_id, pending_chat_title=chat_title)
    await state.set_state(GroupSetupStates.waiting_for_login)
    await callback.message.answer(
        f"Подключение YouGile для группы <b>{chat_title}</b>\n\n"
        "Введи <b>логин</b> от YouGile-аккаунта:"
    )
    await callback.answer()


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


# ── team_ctx direct-entry handlers (skip team selection) ─────────────────────

@router.callback_query(F.data.startswith("team_ctx:members:"))
async def team_ctx_members(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    await state.update_data(members_team_id=team_id)

    members = await get_team_members(team_id, callback.from_user.id)
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    team_title = _team_title(team) if team else team_id

    if not members:
        await callback.message.edit_text(
            f"<b>{team_title}</b>\n\nВ команде нет участников.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
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
        reply_markup=_ctx_members_list_keyboard(members, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:mbr_confirm:"))
async def team_ctx_member_remove_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    team_user_id = callback.data.split(":", 2)[2]
    data = await state.get_data()
    team_id = data.get("members_team_id", "")

    members = await get_team_members(team_id, callback.from_user.id)
    member = next((m for m in members if str(m.get("id")) == team_user_id), None)
    if member is None:
        await callback.message.edit_text(
            "Участник не найден.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    name_parts = []
    if member.get("firstName"):
        name_parts.append(member["firstName"])
    if member.get("lastName"):
        name_parts.append(member["lastName"])
    name = " ".join(name_parts) if name_parts else "Без имени"
    login = member.get("telegramLogin")
    display = f"{name} (@{login})" if login else name

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"team_ctx:mbr_remove:{team_user_id}")],
        [InlineKeyboardButton(text="← Отмена", callback_data=f"team_ctx:members:{team_id}")],
    ])
    await callback.message.edit_text(
        f"Удалить <b>{display}</b> из команды?",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:mbr_remove:"))
async def team_ctx_member_remove(callback: CallbackQuery, state: FSMContext) -> None:
    team_user_id = callback.data.split(":", 2)[2]
    data = await state.get_data()
    team_id = data.get("members_team_id", "")

    ok = await remove_team_member(team_id, team_user_id, callback.from_user.id)
    if not ok:
        await callback.message.edit_text(
            "Не удалось удалить участника. Попробуйте позже.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    members = await get_team_members(team_id, callback.from_user.id)
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    team_title = _team_title(team) if team else team_id

    if not members:
        await callback.message.edit_text(
            f"✅ Участник удалён.\n\n<b>{team_title}</b>\n\nВ команде больше нет участников.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    lines = [f"✅ Участник удалён.\n\n<b>Участники: {team_title}</b> ({len(members)})\n"]
    for m in members:
        role_label = "менеджер 🔑" if m.get("role") == "MANAGER" else "участник"
        name_parts = []
        if m.get("firstName"):
            name_parts.append(m["firstName"])
        if m.get("lastName"):
            name_parts.append(m["lastName"])
        name = " ".join(name_parts) if name_parts else "Без имени"
        login = m.get("telegramLogin")
        display = f"{name} (@{login})" if login else name
        lines.append(f"• {display} — {role_label}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=_ctx_members_list_keyboard(members, team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:link_chat:"))
async def team_ctx_link_chat(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    await state.clear()

    chats = await get_pending_team_chats(callback.from_user.id)
    if not chats:
        await callback.message.edit_text(
            "<b>Привязка чата</b>\n\n"
            "Пока нет чатов для привязки.\n\n"
            "Добавьте бота в нужный групповой чат — после этого он появится здесь.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    await state.update_data(ctx_link_team_id=team_id)
    await callback.message.edit_text(
        "<b>Привязка чата к команде</b>\n\nВыберите чат, куда вы добавили бота:",
        reply_markup=manager_chat_select_keyboard(chats, "ctx_link_select"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manager:ctx_link_select:"))
async def team_ctx_link_chat_select(callback: CallbackQuery, state: FSMContext) -> None:
    raw_chat_id = callback.data.split(":", 2)[2]
    data = await state.get_data()
    team_id = data.get("ctx_link_team_id")
    await state.clear()

    if not team_id:
        await callback.message.edit_text("Сессия устарела. Начните привязку заново.")
        await callback.answer()
        return

    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.edit_text(
            "Не удалось определить чат.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    pending_chats = await get_pending_team_chats(callback.from_user.id)
    pending_chat = next((c for c in pending_chats if c.get("telegramChatId") == chat_id), None)
    chat_title = (pending_chat.get("chatTitle") if pending_chat else None) or str(chat_id)

    ok = await link_chat_to_team(team_id, chat_id, telegram_id=callback.from_user.id, chat_title=chat_title)
    if not ok:
        await callback.message.edit_text(
            "Не удалось привязать чат. Попробуйте позже.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    await _send_join_link_to_group(callback, chat_id, team_id)
    await callback.message.edit_text(
        f"✅ Чат <b>{chat_title}</b> привязан к команде.",
        reply_markup=back_to_team_ctx_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:update:"))
async def team_ctx_update(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас больше нет доступа к ней.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    await state.update_data(
        manager_update_team_id=team_id,
        manager_update_fields={},
        manager_update_ctx_team_id=team_id,
    )
    await state.set_state(ManagerUpdateStates.waiting_for_chat_title)
    await callback.message.edit_text(
        f"<b>Переименование команды</b>\n\n{_format_team(team)}\n\n"
        "Введите новое название команды или пропустите шаг:",
        reply_markup=manager_skip_keyboard("manager:update_skip_chat_title"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:deactivate:"))
async def team_ctx_deactivate(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 2)[2]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас больше нет доступа к ней.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    if team.get("telegramChatId") is None:
        await callback.message.edit_text(
            "У команды нет привязанного Telegram-чата, поэтому деактивировать её через эту кнопку нельзя.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"team_ctx:deactivate_confirm:{team_id}")],
        [InlineKeyboardButton(text="← Отмена", callback_data=f"team_ctx:manager:{team_id}")],
    ])
    await callback.message.edit_text(
        "<b>Подтвердите деактивацию</b>\n\n" + _format_team(team),
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:deactivate_confirm:"))
async def team_ctx_deactivate_confirm(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 2)[2]
    team = await _get_team_for_manager(callback.from_user.id, team_id)
    if team is None:
        await callback.message.edit_text(
            "Команда не найдена.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    chat_id = team.get("telegramChatId")
    if chat_id is None:
        await callback.message.edit_text(
            "У команды нет привязанного Telegram-чата.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    ok = await deactivate_team(int(chat_id), telegram_id=callback.from_user.id)
    if not ok:
        await callback.message.edit_text(
            "Не удалось деактивировать команду. Попробуйте позже.",
            reply_markup=back_to_team_ctx_keyboard(team_id),
        )
        await callback.answer()
        return

    from keyboards.member import back_to_teams_keyboard
    await callback.message.edit_text(
        f"⛔ Команда <b>{_team_title(team)}</b> деактивирована.",
        reply_markup=back_to_teams_keyboard(),
    )
    await callback.answer()


def _ctx_members_list_keyboard(members: list[dict], team_id: str):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for member in members:
        role = member.get("role", "USER")
        display = _member_display_short(member)
        if role == "USER":
            member_user_id = member["id"]
            buttons.append([
                InlineKeyboardButton(text=display, callback_data="noop"),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"team_ctx:mbr_confirm:{member_user_id}",
                ),
            ])
        else:
            buttons.append([InlineKeyboardButton(text=f"{display} 🔑", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="← Назад к команде", callback_data=f"team_ctx:manager:{team_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _member_display_short(member: dict) -> str:
    parts = []
    if member.get("firstName"):
        parts.append(member["firstName"])
    if member.get("lastName"):
        parts.append(member["lastName"])
    name = " ".join(parts) if parts else "Без имени"
    login = member.get("telegramLogin")
    return f"{name} (@{login})" if login else name
