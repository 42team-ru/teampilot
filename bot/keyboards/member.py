from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE = 30
_MAX_TEAMS = 8


def _section(title: str) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=f"━━ {title} ━━", callback_data="noop")]


def _rows(buttons: list[InlineKeyboardButton], width: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[index:index + width] for index in range(0, len(buttons), width)]


def member_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        _section("Работа"),
        [
            InlineKeyboardButton(text="📥 Мои задачи", callback_data="member:mytasks"),
            InlineKeyboardButton(text="🏢 Команды", callback_data="member:teams_overview"),
        ],
        _section("Навигация"),
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
    team_buttons: list[InlineKeyboardButton] = []
    for team in managed_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        team_buttons.append(InlineKeyboardButton(
            text=f"🔑 {title}",
            callback_data=f"team_ctx:manager:{team['id']}",
        ))
    for team in member_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        team_buttons.append(InlineKeyboardButton(
            text=f"👤 {title}",
            callback_data=f"team_ctx:member:{team['id']}",
        ))
    buttons.extend(_rows(team_buttons))
    buttons.append([InlineKeyboardButton(text="← Главное меню", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_context_manager_keyboard(
    team_id: str,
    has_chat: bool = True,
    pending_count: int | None = None,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if has_chat:
        pending_label = "🆕 Новые задачи"
        if pending_count:
            pending_label = f"{pending_label} ({pending_count})"
        buttons.append(_section("Задачи"))
        buttons.extend(_rows([
            InlineKeyboardButton(text=pending_label, callback_data=f"mgr:pending:{team_id}:0"),
            InlineKeyboardButton(text="📥 Мои задачи", callback_data=f"tasks:team_my:{team_id}:active:0"),
            InlineKeyboardButton(text="📋 Задачи команды", callback_data=f"tasks:team:{team_id}:active:0"),
            InlineKeyboardButton(text="📊 Доска", callback_data=f"tasks_board:team:{team_id}"),
        ]))
        buttons.append(_section("Файлы"))
        buttons.append([InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")])
    buttons.append(_section("Управление командой"))
    buttons.extend(_rows([
        InlineKeyboardButton(text="👥 Участники", callback_data=f"team_ctx:members:{team_id}"),
        InlineKeyboardButton(text="🔗 Привязать чат", callback_data=f"team_ctx:link_chat:{team_id}"),
        InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"team_ctx:update:{team_id}"),
        InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"team_ctx:deactivate:{team_id}"),
    ]))
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_context_member_keyboard(team_id: str = "", has_chat: bool = True) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if has_chat and team_id:
        buttons.append(_section("Задачи"))
        buttons.extend(_rows([
            InlineKeyboardButton(text="📥 Мои задачи", callback_data=f"tasks:team_my:{team_id}:active:0"),
            InlineKeyboardButton(text="📋 Задачи команды", callback_data=f"tasks:team:{team_id}:active:0"),
        ]))
        buttons.append(_section("Файлы"))
        buttons.append([InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")])
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def upload_waiting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отменить загрузку", callback_data="upload:cancel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])


def back_to_teams_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")],
    ])


def back_to_member_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="member:back")],
    ])
