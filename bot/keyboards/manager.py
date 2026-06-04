from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE_LEN = 32
_MAX_TEAMS = 8


def manager_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="member:back")],
    ])


def manager_skip_keyboard(skip_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=skip_callback)],
        [InlineKeyboardButton(text="✖ Отмена", callback_data="manager:update_cancel")],
    ])


def manager_team_select_keyboard(teams: list[dict], action: str) -> InlineKeyboardMarkup:
    buttons = []
    for team in teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team["id"])[:_MAX_TITLE_LEN]
        buttons.append([InlineKeyboardButton(
            text=f"👥 {title}",
            callback_data=f"manager:{action}:{team['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manager_chat_select_keyboard(chats: list, action: str) -> InlineKeyboardMarkup:
    buttons = []
    for chat in chats[:_MAX_TEAMS]:
        title = (chat.get("chatTitle") or str(chat["telegramChatId"]))[:_MAX_TITLE_LEN]
        buttons.append([InlineKeyboardButton(
            text=f"💬 {title}",
            callback_data=f"manager:{action}:{chat['telegramChatId']}",
        )])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manager_deactivate_confirm_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"manager:deactivate_confirm:{team_id}")],
        [InlineKeyboardButton(text="← Назад", callback_data="manager:deactivate")],
    ])


def manager_members_list_keyboard(members: list[dict], team_id: str) -> InlineKeyboardMarkup:
    buttons = []
    for member in members:
        role = member.get("role", "USER")
        display = _member_display(member)
        if role == "USER":
            member_user_id = member["id"]
            buttons.append([
                InlineKeyboardButton(text=display, callback_data="noop"),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"manager:mbr_confirm:{member_user_id}",
                ),
            ])
        else:
            buttons.append([InlineKeyboardButton(text=f"{display} 🔑", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="manager:members")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manager_member_remove_confirm_keyboard(team_user_id: str, team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"manager:mbr_remove:{team_user_id}")],
        [InlineKeyboardButton(text="← Отмена", callback_data=f"manager:members_list:{team_id}")],
    ])


def _member_display(member: dict) -> str:
    parts = []
    if member.get("firstName"):
        parts.append(member["firstName"])
    if member.get("lastName"):
        parts.append(member["lastName"])
    name = " ".join(parts) if parts else "Без имени"
    login = member.get("telegramLogin")
    return f"{name} (@{login})" if login else name
