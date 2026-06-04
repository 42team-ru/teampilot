from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from services.task_service import get_task_by_id, get_tasks

router = Router()

_VALID_STATUSES = {"OPEN", "IN_PROGRESS", "REVIEW", "BLOCKED", "DONE", "CANCELLED"}

_STATUS_EMOJI = {
    "OPEN": "🆕",
    "IN_PROGRESS": "🔄",
    "REVIEW": "👀",
    "BLOCKED": "🚫",
    "DONE": "✅",
    "CANCELLED": "❌",
}


def _format_task_row(task: dict) -> str:
    status = task.get("status", "")
    emoji = _STATUS_EMOJI.get(status, "📌")
    title = task.get("title") or "—"
    assignee = task.get("assignee") or {}
    assignee_name = (
        assignee.get("telegramLogin")
        or f"{assignee.get('firstName', '')} {assignee.get('lastName', '')}".strip()
        or "—"
    )
    deadline = task.get("deadline") or "—"
    if deadline != "—":
        deadline = deadline[:10]  # yyyy-mm-dd

    return f"{emoji} <b>{title}</b> [{status}]\n  👤 {assignee_name}  ⏰ {deadline}"


def _format_task_card(task: dict) -> str:
    status = task.get("status", "")
    sync = task.get("syncStatus", "")
    title = task.get("title") or "—"
    description = task.get("description") or "—"
    deadline = (task.get("deadline") or "—")[:10] if task.get("deadline") else "—"
    created_at = (task.get("createdAt") or "—")[:10] if task.get("createdAt") else "—"

    def _person(info: dict | None) -> str:
        if not info:
            return "—"
        name = (
            info.get("telegramLogin")
            or f"{info.get('firstName', '')} {info.get('lastName', '')}".strip()
            or "—"
        )
        return f"@{name}" if info.get("telegramLogin") else name

    assignee = _person(task.get("assignee"))
    author = _person(task.get("author"))

    lines = [
        f"📋 <b>{title}</b>",
        f"",
        f"<b>Статус:</b> {status}  <b>Синхронизация:</b> {sync}",
        f"<b>Исполнитель:</b> {assignee}",
        f"<b>Автор:</b> {author}",
        f"<b>Дедлайн:</b> {deadline}",
        f"<b>Создана:</b> {created_at}",
        f"",
        f"<b>Описание:</b>\n{description}",
    ]
    return "\n".join(lines)


# ── /tasks [статус] — список задач чата ──────────────────────────────────────

@router.message(Command("tasks"))
async def cmd_tasks(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("⚠️ Команда /tasks работает только в групповом чате.")
        return

    args = message.text.split(maxsplit=1)
    raw_status = args[1].strip().upper() if len(args) > 1 else None

    if raw_status and raw_status not in _VALID_STATUSES:
        valid = ", ".join(sorted(_VALID_STATUSES))
        await message.answer(
            f"❌ Неверный статус <b>{raw_status}</b>.\n"
            f"Допустимые значения: {valid}"
        )
        return

    tasks = await get_tasks(message.chat.id, telegram_id=message.from_user.id, status=raw_status)

    if not tasks:
        status_label = f" со статусом <b>{raw_status}</b>" if raw_status else ""
        await message.answer(f"📭 Задач{status_label} не найдено.")
        return

    header = f"📋 <b>Задачи</b>"
    if raw_status:
        header += f" [{raw_status}]"
    header += f" ({len(tasks)})\n"

    rows = [header] + [_format_task_row(t) for t in tasks]
    await message.answer("\n\n".join(rows))


# ── /task <uuid> — карточка задачи ───────────────────────────────────────────

@router.message(Command("task"))
async def cmd_task(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /task <id>\nПример: /task 550e8400-e29b-41d4-a716-446655440000")
        return

    task_id = args[1].strip()
    task = await get_task_by_id(task_id, telegram_id=message.from_user.id)

    if task is None:
        await message.answer(f"❌ Задача <code>{task_id}</code> не найдена.")
        return

    await message.answer(_format_task_card(task))
