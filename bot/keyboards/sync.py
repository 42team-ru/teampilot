from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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


def build_sync_summary_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Отчёт по участникам", callback_data=f"syncsum:{team_id}:0")],
    ])


def build_sync_member_keyboard(team_id: str, index: int, total: int) -> InlineKeyboardMarkup:
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"syncsum:{team_id}:{index - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="syncsum:noop"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"syncsum:{team_id}:{index + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="↩️ Назад к итогам", callback_data=f"syncsum:{team_id}:back")],
    ])


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
