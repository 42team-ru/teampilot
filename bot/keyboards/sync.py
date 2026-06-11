from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_sync_draft_keyboard(group_chat_id: int, item_index: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data=f"sync_confirm:{group_chat_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sync_reject:{group_chat_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить задачу", callback_data=f"sync_edit:{group_chat_id}:{item_index}"),
        ],
    ])


def build_reject_choice_keyboard(group_chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Выбрать из активных задач", callback_data=f"sync_pick_list:{group_chat_id}")],
        [InlineKeyboardButton(text="➕ Создать новую задачу", callback_data=f"sync_create_new:{group_chat_id}")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"sync_skip_new:{group_chat_id}")],
    ])


def build_sync_multi_choice_keyboard(items: list, group_chat_id: int) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        if item.task_id:
            title = (item.task_title or "Задача")[:50]
            tid = item.task_id.replace("-", "")
            rows.append([
                InlineKeyboardButton(
                    text=f"📌 {title}",
                    callback_data=f"sync_pick_task:{group_chat_id}:{tid}",
                )
            ])
    rows.append([
        InlineKeyboardButton(text="✏️ Переформулировать", callback_data=f"sync_edit:{group_chat_id}:1"),
    ])
    rows.append([
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"sync_skip_new:{group_chat_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_active_tasks_keyboard(tasks: list[dict], group_chat_id: int) -> InlineKeyboardMarkup:
    rows = []
    for task in tasks[:10]:
        tid = task["id"].replace("-", "")
        rows.append([
            InlineKeyboardButton(
                text=f"📌 {task['title'][:50]}",
                callback_data=f"sync_pick_task:{group_chat_id}:{tid}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"sync_skip_new:{group_chat_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_proposal_approval_keyboard(proposal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"sync_prop_approve:{proposal_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sync_prop_reject:{proposal_id}"),
        ],
    ])


def build_task_approval_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"sync_task_approve:{task_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sync_task_reject:{task_id}"),
        ],
    ])


def _truncate_bytes(s: str, max_bytes: int) -> str:
    """Truncate string so its UTF-8 encoding fits within max_bytes."""
    encoded = s.encode("utf-8")
    if len(encoded) <= max_bytes:
        return s
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def build_excuse_keyboard(teams: list[dict], reason: str) -> InlineKeyboardMarkup:
    """teams: list of {teamId: str, teamName: str}"""
    builder = InlineKeyboardBuilder()
    # Telegram callback_data limit is 64 BYTES (not chars).
    # "excuse_team:<uuid36>:<reason>" — fixed prefix is 49 bytes, reason budget: 15 bytes
    # "excuse_all:<reason>"           — fixed prefix is 11 bytes, reason budget: 53 bytes
    reason_for_team = _truncate_bytes(reason, 15)
    reason_for_all = _truncate_bytes(reason, 53)
    for team in teams:
        builder.button(
            text=team["teamName"],
            callback_data=f"excuse_team:{team['teamId']}:{reason_for_team}",
        )
    builder.button(text="Все команды", callback_data=f"excuse_all:{reason_for_all}")
    builder.adjust(1)
    return builder.as_markup()
