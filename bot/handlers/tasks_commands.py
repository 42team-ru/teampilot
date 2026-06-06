from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from html import escape
from uuid import UUID as _UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.task_service import get_task_by_id, get_tasks, get_tasks_page, get_team_columns
from services.team_service import get_member_teams, get_my_teams, get_team_members

router = Router()

_DISPLAY_TZ = timezone(timedelta(hours=3))
_ACTIVE_STATUSES = {"ACTIVE", "OPEN", "IN_PROGRESS", "REVIEW", "BLOCKED"}
_BOARD_WORK_STATUSES = {"ACTIVE", "OPEN", "IN_PROGRESS", "BLOCKED"}
_TASKS_PAGE_SIZE = 5

_STATUS_EMOJI = {
    "ACTIVE": "📌",
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


def _normalize_filter_key(raw: str | None) -> str:
    """Return "all" (active), "done" (completed), "every" (all), or a column UUID string."""
    if not raw:
        return "all"
    lower = raw.lower()
    if lower in {"done", "completed"}:
        return "done"
    if lower in {"all", "active"}:
        return "all"
    if lower in {"every", "все"}:
        return "every"
    try:
        _UUID(raw)
        return lower
    except ValueError:
        return "all"


def _filter_to_backend(filter_key: str) -> tuple[str | None, bool | None]:
    """Return (column_id, completed).
    "all"   → completed=False  (активные, не завершённые)
    "every" → completed=None   (все задачи)
    "done"  → completed=True   (завершённые)
    UUID    → columnId filter, completed=None
    """
    if filter_key == "done":
        return None, True
    if filter_key == "every":
        return None, None
    try:
        _UUID(filter_key)
        return filter_key, None
    except ValueError:
        return None, False  # "all" и любой неизвестный → активные


def _safe_page(raw_page: str | int | None) -> int:
    try:
        return max(int(raw_page), 0)
    except (TypeError, ValueError):
        return 0


def _tasks_callback(
    scope: str,
    filter_key: str,
    page: int,
    target_id: str | int | None = None,
) -> str:
    if scope in {"team", "team_my", "user"}:
        return f"tasks:{scope}:{target_id}:{filter_key}:{page}"
    return f"tasks:{scope}:{filter_key}:{page}"


def _local_page(tasks: list[dict], page: int, size: int = _TASKS_PAGE_SIZE) -> dict:
    total = len(tasks)
    total_pages = (total + size - 1) // size if total else 0
    page = min(max(page, 0), max(total_pages - 1, 0))
    start = page * size
    content = tasks[start:start + size]
    return {
        "content": content,
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages,
        "first": page == 0,
        "last": total_pages == 0 or page >= total_pages - 1,
        "empty": not content,
    }


def _page_number(page_data: dict) -> int:
    return int(page_data.get("page") or 0)


def _total_pages(page_data: dict) -> int:
    return int(page_data.get("totalPages") or 0)


def _total_elements(page_data: dict) -> int:
    return int(page_data.get("totalElements") or len(page_data.get("content", [])))


async def _fetch_tasks_page(**kwargs) -> dict:
    requested_page = _safe_page(kwargs.get("page"))
    kwargs["page"] = requested_page
    page_data = await get_tasks_page(**kwargs)

    total_pages = _total_pages(page_data)
    if requested_page > 0 and total_pages and not page_data.get("content") and requested_page >= total_pages:
        kwargs["page"] = total_pages - 1
        page_data = await get_tasks_page(**kwargs)

    return page_data


def _task_action_rows(task: dict, index: int) -> list[list[InlineKeyboardButton]]:
    task_id = task.get("id")
    if not task_id:
        return []

    transitions = {
        "OPEN": [("🔄 В работу", "in_progress"), ("✅ Готово", "done"), ("⏸ Блок", "blocked")],
        "IN_PROGRESS": [("✅ Готово", "done"), ("⏸ Блок", "blocked")],
        "REVIEW": [("✅ Принять", "done"), ("🔄 В работу", "in_progress")],
        "BLOCKED": [("🔄 Снять блок", "in_progress"), ("🗑 Отменить", "cancelled")],
    }
    first_row = [
        InlineKeyboardButton(text=f"{index}. 👁 Детали", callback_data=f"task_show:{task_id}")
    ]
    action_specs = list(transitions.get(task.get("status", ""), []))
    if (
        _is_overdue(task)
        and task.get("status") in _ACTIVE_STATUSES
        and all(status != "cancelled" for _, status in action_specs)
    ):
        action_specs.append(("🗑 Отменить", "cancelled"))

    actions = [
        InlineKeyboardButton(text=f"{index}. {label}", callback_data=f"status:{task_id}:{status}")
        for label, status in action_specs
    ]

    rows = [[*first_row, *actions[:1]]]
    for start in range(1, len(actions), 2):
        rows.append(actions[start:start + 2])
    return rows


def _tasks_keyboard(
    page_data: dict,
    *,
    scope: str,
    filter_key: str,
    columns: list[dict],
    target_id: str | int | None = None,
    back_data: str | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    page = _page_number(page_data)
    total_pages = _total_pages(page_data)
    tasks = page_data.get("content", [])
    start_index = page * int(page_data.get("size") or _TASKS_PAGE_SIZE) + 1

    # For chat scope with columns: dynamic column buttons + "Завершённые"
    # For other scopes: simple "Активные / Завершённые" toggle
    if scope == "chat" and columns:
        filter_buttons: list[InlineKeyboardButton] = []
        for col in columns:
            col_id = str(col.get("id", ""))
            col_title = col.get("title") or "Колонка"
            is_selected = filter_key == col_id
            filter_buttons.append(InlineKeyboardButton(
                text=("✓ " if is_selected else "") + col_title,
                callback_data=_tasks_callback(scope, col_id, 0, target_id),
            ))
        filter_buttons.append(InlineKeyboardButton(
            text=("✓ " if filter_key == "done" else "") + "✅ Завершённые",
            callback_data=_tasks_callback(scope, "done", 0, target_id),
        ))
        filter_buttons.append(InlineKeyboardButton(
            text=("✓ " if filter_key == "every" else "") + "🗂 Все",
            callback_data=_tasks_callback(scope, "every", 0, target_id),
        ))
        for i in range(0, len(filter_buttons), 2):
            rows.append(filter_buttons[i:i + 2])
    else:
        rows.append([
            InlineKeyboardButton(
                text=("✓ " if filter_key == "all" else "") + "📋 Активные",
                callback_data=_tasks_callback(scope, "all", 0, target_id),
            ),
            InlineKeyboardButton(
                text=("✓ " if filter_key == "done" else "") + "✅ Завершённые",
                callback_data=_tasks_callback(scope, "done", 0, target_id),
            ),
            InlineKeyboardButton(
                text=("✓ " if filter_key == "every" else "") + "🗂 Все",
                callback_data=_tasks_callback(scope, "every", 0, target_id),
            ),
        ])

    for offset, task in enumerate(tasks):
        rows.extend(_task_action_rows(task, start_index + offset))

    if total_pages > 1:
        prev_page = max(page - 1, 0)
        next_page = min(page + 1, total_pages - 1)
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=_tasks_callback(scope, filter_key, prev_page, target_id)),
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=_tasks_callback(scope, filter_key, page, target_id)),
            InlineKeyboardButton(text="▶️", callback_data=_tasks_callback(scope, filter_key, next_page, target_id)),
        ])

    rows.append([InlineKeyboardButton(
        text="🔄 Обновить",
        callback_data=_tasks_callback(scope, filter_key, page, target_id),
    )])
    if back_data:
        rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _refresh_keyboard(refresh_data: str, back_data: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🔄 Обновить", callback_data=refresh_data)]]
    if back_data:
        rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_task_page(
    page_data: dict,
    header: str,
    *,
    scope: str,
    filter_key: str,
    columns: list[dict],
    target_id: str | int | None = None,
    back_data: str | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    tasks = page_data.get("content", [])
    total = _total_elements(page_data)
    total_pages = _total_pages(page_data)
    page = _page_number(page_data)

    if filter_key == "done":
        filter_label = "Завершённые"
    elif filter_key == "every":
        filter_label = "Все"
    else:
        col = next((c for c in columns if str(c.get("id")) == filter_key), None)
        filter_label = col.get("title") if col else "Активные"

    lines = [
        header,
        f"Фильтр: <b>{escape(filter_label)}</b> · Всего: <b>{total}</b>",
    ]
    if total_pages:
        lines.append(f"Страница: <b>{page + 1}/{total_pages}</b>")

    if not tasks:
        lines.append("")
        lines.append("Задач по этому фильтру нет.")
    else:
        start_index = page * int(page_data.get("size") or _TASKS_PAGE_SIZE) + 1
        lines.append("")
        lines.extend(
            _format_task_row(task, start_index + offset)
            for offset, task in enumerate(tasks)
        )

    return "\n\n".join(lines), _tasks_keyboard(
        page_data,
        scope=scope,
        filter_key=filter_key,
        columns=columns,
        target_id=target_id,
        back_data=back_data,
    )


async def _render_my_tasks(
    telegram_id: int,
    *,
    filter_key: str = "all",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    _, completed = _filter_to_backend(filter_key)
    page_data = await _fetch_tasks_page(
        telegram_id=telegram_id,
        assignee=telegram_id,
        completed=completed,
        page=page,
        size=_TASKS_PAGE_SIZE,
    )
    return _format_task_page(
        page_data,
        "📋 <b>Твои задачи</b>",
        scope="my",
        filter_key=filter_key,
        columns=[],
        back_data="member:back",
    )


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
        get_tasks(chat_id=chat_id, telegram_id=telegram_id, completed=False, size=100)
        for team in teams
        if (chat_id := _team_chat_id(team)) is not None
    ]
    if not calls:
        return []

    result_sets = await asyncio.gather(*calls)
    return [task for result in result_sets for task in result]


async def _render_chat_tasks(
    chat_id: int,
    telegram_id: int,
    *,
    filter_key: str = "all",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    column_id, completed = _filter_to_backend(filter_key)
    results = await asyncio.gather(
        get_team_columns(chat_id, telegram_id),
        _fetch_tasks_page(
            chat_id=chat_id,
            telegram_id=telegram_id,
            column_id=column_id,
            completed=completed,
            page=page,
            size=_TASKS_PAGE_SIZE,
        ),
        return_exceptions=True,
    )
    columns = results[0] if isinstance(results[0], list) else []
    page_data = results[1]
    if isinstance(page_data, Exception):
        raise page_data
    return _format_task_page(
        page_data,
        "📋 <b>Задачи команды</b>",
        scope="chat",
        filter_key=filter_key,
        columns=columns,
    )


async def _render_team_tasks(
    manager_id: int,
    team_id: str,
    *,
    filter_key: str = "all",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup] | None:
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(manager_id),
        get_member_teams(manager_id),
    )
    team = next((t for t in manager_teams if str(t.get("id")) == team_id), None)
    back_scope = "manager"
    if team is None:
        team = next((t for t in member_teams if str(t.get("id")) == team_id), None)
        back_scope = "member"
    if team is None:
        return None

    chat_id = _team_chat_id(team)
    if chat_id is None:
        return None

    _, completed = _filter_to_backend(filter_key)
    page_data = await _fetch_tasks_page(
        chat_id=chat_id,
        telegram_id=manager_id,
        completed=completed,
        page=page,
        size=_TASKS_PAGE_SIZE,
    )
    title = escape(team.get("chatTitle") or team_id)
    return _format_task_page(
        page_data,
        f"📋 <b>Задачи команды: {title}</b>",
        scope="team",
        filter_key=filter_key,
        columns=[],
        target_id=team_id,
        back_data=f"team_ctx:{back_scope}:{team_id}",
    )


async def _render_team_my_tasks(
    telegram_id: int,
    team_id: str,
    *,
    filter_key: str = "all",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup] | None:
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(telegram_id),
        get_member_teams(telegram_id),
    )
    team = next((t for t in manager_teams if str(t.get("id")) == team_id), None)
    back_scope = "manager"
    if team is None:
        team = next((t for t in member_teams if str(t.get("id")) == team_id), None)
        back_scope = "member"
    if team is None:
        return None

    chat_id = _team_chat_id(team)
    if chat_id is None:
        return None

    _, completed = _filter_to_backend(filter_key)
    page_data = await _fetch_tasks_page(
        chat_id=chat_id,
        telegram_id=telegram_id,
        assignee=telegram_id,
        completed=completed,
        page=page,
        size=_TASKS_PAGE_SIZE,
    )
    title = escape(team.get("chatTitle") or team_id)
    return _format_task_page(
        page_data,
        f"📋 <b>Мои задачи: {title}</b>",
        scope="team_my",
        filter_key=filter_key,
        columns=[],
        target_id=team_id,
        back_data=f"team_ctx:{back_scope}:{team_id}",
    )


def _column_tasks_keyboard(
    page_data: dict,
    *,
    column_id: str,
    back_data: str | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    page = _page_number(page_data)
    total_pages = _total_pages(page_data)
    tasks = page_data.get("content", [])
    start_index = page * int(page_data.get("size") or _TASKS_PAGE_SIZE) + 1

    for offset, task in enumerate(tasks):
        rows.extend(_task_action_rows(task, start_index + offset))

    if total_pages > 1:
        prev_page = max(page - 1, 0)
        next_page = min(page + 1, total_pages - 1)
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=f"tasks:col:{column_id}:{prev_page}"),
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"tasks:col:{column_id}:{page}"),
            InlineKeyboardButton(text="▶️", callback_data=f"tasks:col:{column_id}:{next_page}"),
        ])

    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"tasks:col:{column_id}:{page}")])
    if back_data:
        rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_column_task_page(
    page_data: dict,
    header: str,
    *,
    column_id: str,
    back_data: str | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    tasks = page_data.get("content", [])
    total = _total_elements(page_data)
    total_pages = _total_pages(page_data)
    page = _page_number(page_data)
    start_index = page * int(page_data.get("size") or _TASKS_PAGE_SIZE) + 1

    lines = [header, f"Всего: <b>{total}</b>"]
    if total_pages > 1:
        lines.append(f"Страница: <b>{page + 1}/{total_pages}</b>")
    if not tasks:
        lines.extend(["", "Задач в этой колонке нет."])
    else:
        lines.append("")
        lines.extend(_format_task_row(task, start_index + offset) for offset, task in enumerate(tasks))

    return "\n\n".join(lines), _column_tasks_keyboard(
        page_data, column_id=column_id, back_data=back_data,
    )


async def _render_team_column_tasks(
    telegram_id: int,
    column_id: str,
    *,
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup] | None:
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(telegram_id),
        get_member_teams(telegram_id),
    )

    team = None
    back_scope = "m"
    col_title = "Колонка"

    for t in manager_teams:
        chat_id = _team_chat_id(t)
        if not chat_id:
            continue
        cols = await get_team_columns(chat_id, telegram_id)
        match = next((c for c in cols if str(c.get("id")) == column_id), None)
        if match:
            team, col_title = t, match.get("title") or col_title
            break

    if team is None:
        for t in member_teams:
            chat_id = _team_chat_id(t)
            if not chat_id:
                continue
            cols = await get_team_columns(chat_id, telegram_id)
            match = next((c for c in cols if str(c.get("id")) == column_id), None)
            if match:
                team, col_title, back_scope = t, match.get("title") or col_title, "u"
                break

    if team is None:
        return None

    page_data = await _fetch_tasks_page(
        telegram_id=telegram_id,
        column_id=column_id,
        page=page,
        size=_TASKS_PAGE_SIZE,
    )
    team_id = str(team.get("id"))
    title = escape(team.get("chatTitle") or team_id)
    return _format_column_task_page(
        page_data,
        f"📌 <b>{escape(col_title)}</b> · {title}",
        column_id=column_id,
        back_data=f"tm:{back_scope}:t:{team_id}",
    )


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


async def _render_team_board(
    telegram_id: int,
    team_id: str,
) -> tuple[str, InlineKeyboardMarkup] | None:
    teams = await get_my_teams(telegram_id)
    team = next((t for t in teams if str(t.get("id")) == team_id), None)
    if team is None or _team_chat_id(team) is None:
        return None

    tasks = await _fetch_board_tasks(telegram_id, [team])
    title = escape(team.get("chatTitle") or team_id)
    text = _format_board(tasks).replace(
        "📊 <b>Доска команды",
        f"📊 <b>Доска: {title}",
        1,
    )
    return text, _refresh_keyboard(f"tasks_board:team:{team_id}", back_data=f"team_ctx:manager:{team_id}")


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
    *,
    filter_key: str = "all",
    page: int = 0,
) -> tuple[str, InlineKeyboardMarkup] | None:
    teams = await _manager_teams_for_context(manager_id, message)
    if not teams:
        return None

    telegram_id = member.get("telegramId")
    if telegram_id is None:
        return (
            f"📋 <b>Задачи {_member_name(member)}</b>\n\n"
            "У участника не указан Telegram ID, задачи открыть не удалось.",
            InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview"),
            ]]),
        )

    _, completed = _filter_to_backend(filter_key)
    calls = [
        get_tasks(
            chat_id=chat_id,
            telegram_id=manager_id,
            assignee=int(telegram_id),
            completed=completed,
            size=100,
        )
        for team in teams
        if (chat_id := _team_chat_id(team)) is not None
    ]
    result_sets = await asyncio.gather(*calls) if calls else []
    tasks = [task for result in result_sets for task in result]
    return _format_task_page(
        _local_page(tasks, page),
        f"📋 <b>Задачи {_member_name(member)}</b>",
        scope="user",
        filter_key=filter_key,
        columns=[],
        target_id=telegram_id,
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

    text, keyboard = await _render_chat_tasks(
        chat_id=message.chat.id,
        telegram_id=message.from_user.id,
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


def _task_detail_keyboard(task: dict, back_data: str | None = None) -> InlineKeyboardMarkup | None:
    task_id = task.get("id")
    status = task.get("status", "")
    if not task_id:
        return None

    transitions = {
        "OPEN":        [("🔄 В работе", "in_progress"), ("⏸ Заблокировать", "blocked")],
        "IN_PROGRESS": [("✅ Готово", "done"), ("⏸ Блок", "blocked")],
        "REVIEW":      [("✅ Принять", "done"), ("🔄 Вернуть в работу", "in_progress")],
        "BLOCKED":     [("🔄 Разблокировать", "in_progress"), ("🗑 Отменить", "cancelled")],
    }
    actions = transitions.get(status, [])
    rows = []
    if actions:
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"status:{task_id}:{cb}")
            for label, cb in actions
        ])
    rows.append([InlineKeyboardButton(text="🔄 Обновить карточку", callback_data=f"task_show:{task_id}")])
    if back_data:
        rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_data)])
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

    await message.answer(
        _format_task_card(task),
        reply_markup=_task_detail_keyboard(task, back_data="tasks:my:all:0"),
    )


@router.callback_query(F.data.startswith("task_show:"))
async def show_task_details(callback: CallbackQuery) -> None:
    task_id = (callback.data or "").split(":", 1)[1]
    task = await get_task_by_id(task_id, telegram_id=callback.from_user.id)
    if task is None:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    back_data = "tasks:my:all:0" if callback.message.chat.type == "private" else "tasks:chat:all:0"
    try:
        await callback.message.edit_text(
            _format_task_card(task),
            reply_markup=_task_detail_keyboard(task, back_data=back_data),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Карточка открыта")


@router.callback_query(F.data.startswith("tasks:"))
async def navigate_tasks(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    parts = (callback.data or "").split(":")
    scope = parts[1] if len(parts) > 1 else ""

    if scope in {"my", "chat"} and len(parts) == 4:
        filter_key = _normalize_filter_key(parts[2])
        page = _safe_page(parts[3])
        if scope == "my":
            text, keyboard = await _render_my_tasks(
                callback.from_user.id,
                filter_key=filter_key,
                page=page,
            )
        else:
            text, keyboard = await _render_chat_tasks(
                callback.message.chat.id,
                callback.from_user.id,
                filter_key=filter_key,
                page=page,
            )
    elif scope in {"team", "team_my"} and len(parts) == 5:
        team_id = parts[2]
        filter_key = _normalize_filter_key(parts[3])
        page = _safe_page(parts[4])
        if scope == "team":
            rendered = await _render_team_tasks(
                callback.from_user.id,
                team_id,
                filter_key=filter_key,
                page=page,
            )
        else:
            rendered = await _render_team_my_tasks(
                callback.from_user.id,
                team_id,
                filter_key=filter_key,
                page=page,
            )
        if rendered is None:
            await callback.answer("Команда недоступна или чат не привязан", show_alert=True)
            return
        text, keyboard = rendered
    elif scope == "col" and len(parts) == 4:
        column_id = parts[2]
        page = _safe_page(parts[3])
        rendered = await _render_team_column_tasks(
            callback.from_user.id,
            column_id,
            page=page,
        )
        if rendered is None:
            await callback.answer("Колонка недоступна", show_alert=True)
            return
        text, keyboard = rendered
    elif scope == "user" and len(parts) == 5:
        try:
            target_id = int(parts[2])
        except ValueError:
            await callback.answer("Участник недоступен", show_alert=True)
            return

        filter_key = _normalize_filter_key(parts[3])
        page = _safe_page(parts[4])
        teams = await _manager_teams_for_context(callback.from_user.id, callback.message)
        member = await _team_member_by_telegram_id(teams, callback.from_user.id, target_id)
        if member is None:
            await callback.answer("Участник недоступен", show_alert=True)
            return

        rendered = await _render_member_tasks(
            callback.from_user.id,
            callback.message,
            member,
            filter_key=filter_key,
            page=page,
        )
        if rendered is None:
            await callback.answer("Только для менеджера", show_alert=True)
            return
        text, keyboard = rendered
    else:
        await callback.answer("Не удалось открыть задачи", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Готово")


@router.callback_query(F.data.startswith("tasks_board:team:"))
async def show_team_board(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    team_id = (callback.data or "").split(":", 2)[2]
    rendered = await _render_team_board(callback.from_user.id, team_id)
    if rendered is None:
        await callback.answer("Доска доступна только менеджеру команды", show_alert=True)
        return

    text, keyboard = rendered
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Готово")


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
        filter_key = _normalize_filter_key(parts[2])
        text, keyboard = await _render_chat_tasks(
            chat_id=callback.message.chat.id,
            telegram_id=callback.from_user.id,
            filter_key=filter_key,
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
