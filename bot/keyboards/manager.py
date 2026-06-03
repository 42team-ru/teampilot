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
        title = chat.chat_title[:_MAX_TITLE_LEN]
        buttons.append([InlineKeyboardButton(
            text=f"💬 {title}",
            callback_data=f"manager:{action}:{chat.chat_id}",
        )])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manager_deactivate_confirm_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"manager:deactivate_confirm:{team_id}")],
        [InlineKeyboardButton(text="← Назад", callback_data="manager:deactivate")],
    ])
