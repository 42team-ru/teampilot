from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.task_service import get_task_by_id, get_tasks
from services.team_service import get_my_teams, get_team_members

router = Router()

_DISPLAY_TZ = timezone(timedelta(hours=3))
_VALID_STATUSES = {"OPEN", "IN_PROGRESS", "REVIEW", "BLOCKED", "DONE", "CANCELLED"}
_ACTIVE_STATUSES = {"OPEN", "IN_PROGRESS", "REVIEW", "BLOCKED"}
_BOARD_WORK_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED"}

_STATUS_EMOJI = {
    "OPEN": "🆕",
    "IN_PROGRESS": "🔄",
    "REVIEW": "👀",
    "BLOCKED": "⏸",
    "DONE": "✅",
    "CANCELLED": "🗑",
}

_MONTHS_SHORT = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "мая",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}
_MONTHS_FULL = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def _is_my_tasks_question(message: Message) -> bool:
    text = " ".join((message.text or "").strip().lower().split())
    if not text or text.startswith("/"):
        return False
    return (
        "какие у меня задачи" in text
        or text in {"мои задачи", "какие мои задачи", "покажи мои задачи"}
    )


def _parse_deadline(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(_DISPLAY_TZ).date()
    except ValueError:
        return None


def _today():
    return datetime.now(_DISPLAY_TZ).date()


def _short_date(value) -> str:
    return f"{value.day} {_MONTHS_SHORT[value.month]}"


def _full_date(value) -> str:
    return f"{value.day} {_MONTHS_FULL[value.month]}"


def _is_overdue(task: dict) -> bool:
    deadline = _parse_deadline(task.get("deadline"))
    return bool(deadline and deadline < _today() and task.get("status") in _ACTIVE_STATUSES)


def _deadline_line(task: dict) -> str:
    deadline = _parse_deadline(task.get("deadline"))
    if deadline is None:
        return "Дедлайн: не указан"
    if deadline < _today():
        return f"Дедлайн: просрочен (был {_short_date(deadline)})"

    line = f"Дедлайн: {_short_date(deadline)}"
    priority = task.get("priority")
    if priority:
        line += f" · Приоритет: {escape(str(priority).lower())}"
    return line


def _person_name(info: dict | None, default: str = "Без исполнителя") -> str:
    if not info:
        return default

    login = info.get("telegramLogin")
    if login:
        return f"@{escape(str(login))}"

    name = f"{info.get('firstName') or ''} {info.get('lastName') or ''}".strip()
    return escape(name or default)


def _member_name(member: dict | None) -> str:
    if not member:
        return "участника"

    login = member.get("telegramLogin")
    if login:
        return f"@{escape(str(login))}"

    name = f"{member.get('firstName') or ''} {member.get('lastName') or ''}".strip()
    return escape(name or "участника")


def _format_task_row(task: dict, index: int) -> str:
    status = task.get("status", "")
    emoji = _STATUS_EMOJI.get(status, "📌")
    title = escape(task.get("title") or "Без названия")
    return f"{index}. {emoji} <b>{title}</b>\n   {_deadline_line(task)}"


def _format_task_card(task: dict) -> str:
    status = escape(str(task.get("status") or ""))
    sync = escape(str(task.get("syncStatus") or ""))
    title = escape(task.get("title") or "Без названия")
    description = escape(task.get("description") or "—")
    deadline = _deadline_line(task).replace("Дедлайн: ", "", 1)
    created_at = (task.get("createdAt") or "—")[:10] if task.get("createdAt") else "—"

    assignee = _person_name(task.get("assignee"), default="—")
    author = _person_name(task.get("author"), default="—")

    lines = [
        f"📋 <b>{title}</b>",
        "",
        f"<b>Статус:</b> {status}  <b>Синхронизация:</b> {sync}",
        f"<b>Исполнитель:</b> {assignee}",
        f"<b>Автор:</b> {author}",
        f"<b>Дедлайн:</b> {deadline}",
        f"<b>Создана:</b> {escape(created_at)}",
        "",
        f"<b>Описание:</b>\n{description}",
    ]
    return "\n".join(lines)


def _tasks_keyboard(tasks: list[dict], refresh_data: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for index, task in enumerate(tasks, start=1):
        task_id = task.get("id")
        if not task_id:
            continue

        second_button = InlineKeyboardButton(
            text=f"{index}. 🗑 Отменить" if _is_overdue(task) else f"{index}. ⏸ Блок",
            callback_data=f"status:{task_id}:cancelled" if _is_overdue(task) else f"status:{task_id}:blocked",
        )
        rows.append([
            InlineKeyboardButton(text=f"{index}. ✅ Готово", callback_data=f"status:{task_id}:done"),
            second_button,
        ])

    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=refresh_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _refresh_keyboard(refresh_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Обновить", callback_data=refresh_data),
    ]])


def _format_task_list(
    tasks: list[dict],
    header: str,
    refresh_data: str,
    *,
    active_total: bool = True,
) -> tuple[str, InlineKeyboardMarkup]:
    if not tasks:
        empty_text = "Активных задач нет." if active_total else "Задач нет."
        return f"{header}\n\n{empty_text}", _refresh_keyboard(refresh_data)

    lines = [header]
    lines.extend(_format_task_row(task, index) for index, task in enumerate(tasks, start=1))
    total = f"Всего: {len(tasks)} активных" if active_total else f"Всего: {len(tasks)}"
    lines.append(total)
    return "\n\n".join(lines), _tasks_keyboard(tasks, refresh_data)


async def _render_my_tasks(telegram_id: int) -> tuple[str, InlineKeyboardMarkup]:
    tasks = await get_tasks(
        telegram_id=telegram_id,
        assignee=telegram_id,
        status="active",
        size=100,
    )
    return _format_task_list(tasks, "📋 <b>Твои активные задачи:</b>", "tasks_refresh:my")


def _team_chat_id(team: dict) -> int | None:
    chat_id = team.get("telegramChatId")
    if chat_id is None:
        return None
    try:
        return int(chat_id)
    except (TypeError, ValueError):
        return None


async def _manager_teams_for_context(telegram_id: int, message: Message) -> list[dict]:
    teams = await get_my_teams(telegram_id)
    if message.chat.type in {"group", "supergroup"}:
        return [team for team in teams if _team_chat_id(team) == message.chat.id]
    return teams


async def _fetch_board_tasks(telegram_id: int, teams: list[dict]) -> list[dict]:
    calls = [
        get_tasks(chat_id=chat_id, telegram_id=telegram_id, status="active", size=100)
        for team in teams
        if (chat_id := _team_chat_id(team)) is not None
    ]
    if not calls:
        return []

    result_sets = await asyncio.gather(*calls)
    return [task for result in result_sets for task in result]


def _board_task_line(task: dict, *, overdue: bool = False) -> str:
    assignee = _person_name(task.get("assignee"))
    title = escape(task.get("title") or "Без названия")
    deadline = _parse_deadline(task.get("deadline"))
    if deadline is None:
        suffix = ""
    elif overdue:
        suffix = f" (был {_short_date(deadline)})"
    else:
        suffix = f" (до {_short_date(deadline)})"
    return f"  · {assignee}: {title}{suffix}"


def _format_board(tasks: list[dict]) -> str:
    today = _today()
    overdue = [task for task in tasks if _is_overdue(task)]
    overdue_ids = {task.get("id") for task in overdue}
    in_work = [
        task for task in tasks
        if task.get("status") in _BOARD_WORK_STATUSES and task.get("id") not in overdue_ids
    ]
    in_review = [
        task for task in tasks
        if task.get("status") == "REVIEW" and task.get("id") not in overdue_ids
    ]

    lines = [f"📊 <b>Доска команды ({_full_date(today)})</b>", ""]
    sections = [
        ("В работе", in_work, False),
        ("На проверке", in_review, False),
        ("Просрочены", overdue, True),
    ]

    for title, section_tasks, is_overdue in sections:
        lines.append(f"{title} ({len(section_tasks)}):")
        if section_tasks:
            lines.extend(_board_task_line(task, overdue=is_overdue) for task in section_tasks)
        else:
            lines.append("  · нет задач")
        lines.append("")

    return "\n".join(lines).rstrip()


async def _render_board(telegram_id: int, message: Message) -> tuple[str, InlineKeyboardMarkup] | None:
    teams = await _manager_teams_for_context(telegram_id, message)
    if not teams:
        return None

    tasks = await _fetch_board_tasks(telegram_id, teams)
    return _format_board(tasks), _refresh_keyboard("tasks_refresh:board")


async def _team_members_by_username(teams: list[dict], manager_id: int, username: str) -> list[dict]:
    normalized = username.lower().lstrip("@")
    calls = [
        get_team_members(str(team["id"]), manager_id)
        for team in teams
        if team.get("id")
    ]
    if not calls:
        return []

    result_sets = await asyncio.gather(*calls)
    matches: list[dict] = []
    seen: set[int] = set()
    for members in result_sets:
        for member in members:
            telegram_id = member.get("telegramId")
            login = (member.get("telegramLogin") or "").lower()
            if telegram_id is not None and login == normalized and telegram_id not in seen:
                seen.add(telegram_id)
                matches.append(member)
    return matches


async def _team_member_by_telegram_id(teams: list[dict], manager_id: int, telegram_id: int) -> dict | None:
    calls = [
        get_team_members(str(team["id"]), manager_id)
        for team in teams
        if team.get("id")
    ]
    if not calls:
        return None

    result_sets = await asyncio.gather(*calls)
    for members in result_sets:
        for member in members:
            if member.get("telegramId") == telegram_id:
                return member
    return None


async def _render_member_tasks(
    manager_id: int,
    message: Message,
    member: dict,
) -> tuple[str, InlineKeyboardMarkup] | None:
    teams = await _manager_teams_for_context(manager_id, message)
    if not teams:
        return None

    telegram_id = member.get("telegramId")
    if telegram_id is None:
        return _format_task_list([], f"📋 <b>Активные задачи {_member_name(member)}:</b>", "tasks_refresh:my")

    calls = [
        get_tasks(
            chat_id=chat_id,
            telegram_id=manager_id,
            assignee=int(telegram_id),
            status="active",
            size=100,
        )
        for team in teams
        if (chat_id := _team_chat_id(team)) is not None
    ]
    result_sets = await asyncio.gather(*calls) if calls else []
    tasks = [task for result in result_sets for task in result]
    return _format_task_list(
        tasks,
        f"📋 <b>Активные задачи {_member_name(member)}:</b>",
        f"tasks_refresh:user:{telegram_id}",
    )


@router.message(Command("mytasks"))
@router.message(_is_my_tasks_question)
async def cmd_mytasks(message: Message) -> None:
    text, keyboard = await _render_my_tasks(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("board"))
async def cmd_board(message: Message) -> None:
    rendered = await _render_board(message.from_user.id, message)
    if rendered is None:
        await message.answer("🔒 /board доступна только менеджеру этой команды.")
        return

    text, keyboard = rendered
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    raw_arg = args[1].strip() if len(args) > 1 else None

    if raw_arg and raw_arg.startswith("@"):
        await _send_member_tasks_command(message, raw_arg)
        return

    if message.chat.type == "private":
        await message.answer("⚠️ Для личных задач используйте /mytasks. Для задач участника: /tasks @username.")
        return

    raw_status = raw_arg.upper() if raw_arg else None
    if raw_status and raw_status not in _VALID_STATUSES:
        valid = ", ".join(sorted(_VALID_STATUSES))
        await message.answer(
            f"❌ Неверный статус <b>{escape(raw_status)}</b>.\n"
            f"Допустимые значения: {valid}"
        )
        return

    tasks = await get_tasks(
        chat_id=message.chat.id,
        telegram_id=message.from_user.id,
        status=raw_status,
    )

    if not tasks:
        status_label = f" со статусом <b>{escape(raw_status)}</b>" if raw_status else ""
        await message.answer(f"📭 Задач{status_label} не найдено.")
        return

    header = "📋 <b>Задачи</b>"
    if raw_status:
        header += f" [{escape(raw_status)}]"
    header += f" ({len(tasks)})"
    refresh_status = raw_status or "all"
    text, keyboard = _format_task_list(
        tasks,
        header,
        f"tasks_refresh:chat:{refresh_status}",
        active_total=False,
    )
    await message.answer(text, reply_markup=keyboard)


async def _send_member_tasks_command(message: Message, raw_arg: str) -> None:
    username = raw_arg.split()[0].lstrip("@")
    teams = await _manager_teams_for_context(message.from_user.id, message)
    if not teams:
        await message.answer("🔒 /tasks @username доступна только менеджеру этой команды.")
        return

    matches = await _team_members_by_username(teams, message.from_user.id, username)
    if not matches:
        await message.answer(f"Не нашёл участника @{escape(username)} в ваших командах.")
        return

    rendered = await _render_member_tasks(message.from_user.id, message, matches[0])
    if rendered is None:
        await message.answer("🔒 /tasks @username доступна только менеджеру этой команды.")
        return

    text, keyboard = rendered
    await message.answer(text, reply_markup=keyboard)


def _task_detail_keyboard(task: dict) -> InlineKeyboardMarkup | None:
    task_id = task.get("id")
    status = task.get("status", "")
    if not task_id or status not in _ACTIVE_STATUSES:
        return None

    transitions = {
        "OPEN":        [("🔄 В работе", "in_progress"), ("⏸ Заблокировать", "blocked")],
        "IN_PROGRESS": [("✅ Готово", "done"), ("⏸ Блок", "blocked")],
        "REVIEW":      [("✅ Принять", "done"), ("🔄 Вернуть в работу", "in_progress")],
        "BLOCKED":     [("🔄 Разблокировать", "in_progress"), ("🗑 Отменить", "cancelled")],
    }
    actions = transitions.get(status, [])
    if not actions:
        return None

    rows = [[
        InlineKeyboardButton(text=label, callback_data=f"status:{task_id}:{cb}")
        for label, cb in actions
    ]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("task"))
async def cmd_task(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /task <id>\nПример: /task 550e8400-e29b-41d4-a716-446655440000")
        return

    task_id = args[1].strip()
    task = await get_task_by_id(task_id, telegram_id=message.from_user.id)

    if task is None:
        await message.answer(f"❌ Задача <code>{escape(task_id)}</code> не найдена.")
        return

    await message.answer(_format_task_card(task), reply_markup=_task_detail_keyboard(task))


@router.callback_query(F.data.startswith("tasks_refresh:"))
async def refresh_tasks(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    parts = (callback.data or "").split(":")
    kind = parts[1] if len(parts) > 1 else ""

    if kind == "my":
        text, keyboard = await _render_my_tasks(callback.from_user.id)
    elif kind == "board":
        rendered = await _render_board(callback.from_user.id, callback.message)
        if rendered is None:
            await callback.answer("Только для менеджера", show_alert=True)
            return
        text, keyboard = rendered
    elif kind == "chat" and len(parts) == 3:
        raw_status = None if parts[2] == "all" else parts[2]
        tasks = await get_tasks(
            chat_id=callback.message.chat.id,
            telegram_id=callback.from_user.id,
            status=raw_status,
        )
        header = "📋 <b>Задачи</b>"
        if raw_status:
            header += f" [{escape(raw_status)}]"
        header += f" ({len(tasks)})"
        text, keyboard = _format_task_list(
            tasks,
            header,
            f"tasks_refresh:chat:{parts[2]}",
            active_total=False,
        )
    elif kind == "user" and len(parts) == 3:
        try:
            target_id = int(parts[2])
        except ValueError:
            await callback.answer("Не удалось обновить", show_alert=True)
            return

        teams = await _manager_teams_for_context(callback.from_user.id, callback.message)
        member = await _team_member_by_telegram_id(teams, callback.from_user.id, target_id)
        if member is None:
            await callback.answer("Участник недоступен", show_alert=True)
            return

        rendered = await _render_member_tasks(callback.from_user.id, callback.message, member)
        if rendered is None:
            await callback.answer("Только для менеджера", show_alert=True)
            return
        text, keyboard = rendered
    else:
        await callback.answer("Не удалось обновить", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Обновлено")
