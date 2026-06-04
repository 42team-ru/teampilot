from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE = 30
_MAX_TEAMS = 8


def member_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="member:mytasks")],
        [InlineKeyboardButton(text="🏢 Мои команды", callback_data="member:teams_overview")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="member:help")],
    ])


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])


def team_overview_keyboard(
    managed_teams: list[dict],
    member_teams: list[dict],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for team in managed_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        buttons.append([InlineKeyboardButton(
            text=f"🔑 {title}",
            callback_data=f"team_ctx:manager:{team['id']}",
        )])
    for team in member_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        buttons.append([InlineKeyboardButton(
            text=f"👤 {title}",
            callback_data=f"team_ctx:member:{team['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="← Главное меню", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_context_manager_keyboard(team_id: str, has_chat: bool = True) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="👥 Участники команды", callback_data=f"team_ctx:members:{team_id}")],
        [InlineKeyboardButton(text="🔗 Привязать чат", callback_data=f"team_ctx:link_chat:{team_id}")],
        [InlineKeyboardButton(text="✏️ Переименовать команду", callback_data=f"team_ctx:update:{team_id}")],
        [InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"team_ctx:deactivate:{team_id}")],
    ]
    if has_chat:
        buttons.append([InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")])
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_context_member_keyboard(team_id: str = "", has_chat: bool = True) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if has_chat and team_id:
        buttons.append([InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")])
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_teams_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")],
    ])


def back_to_member_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="member:back")],
    ])
