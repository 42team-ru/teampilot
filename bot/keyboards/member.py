from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE = 30
_MAX_TEAMS = 8


def _rows(buttons: list[InlineKeyboardButton], width: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[index:index + width] for index in range(0, len(buttons), width)]


def member_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Мои задачи", callback_data="member:mytasks"),
            InlineKeyboardButton(text="🏢 Команды", callback_data="member:teams_overview"),
        ],
    ])


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])


def my_tasks_team_keyboard(
    managed_teams: list[dict],
    member_teams: list[dict],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    team_buttons: list[InlineKeyboardButton] = []
    for team in managed_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        team_buttons.append(InlineKeyboardButton(
            text=f"🔑 {title}",
            callback_data=f"mytasks:t:{team['id']}",
        ))
    for team in member_teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team.get("id") or "Команда")[:_MAX_TITLE]
        team_buttons.append(InlineKeyboardButton(
            text=f"👤 {title}",
            callback_data=f"mytasks:t:{team['id']}",
        ))
    buttons.extend(_rows(team_buttons))
    buttons.append([InlineKeyboardButton(text="← Главное меню", callback_data="member:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
    has_kanban: bool = True,
) -> InlineKeyboardMarkup:
    menu_buttons: list[InlineKeyboardButton] = []
    if has_chat:
        if not has_kanban:
            tasks_label = "⚠️ Задачи (канбан не настроен)"
        else:
            tasks_label = "📋 Задачи"
            if pending_count:
                tasks_label = f"{tasks_label} ({pending_count} новых)"
        menu_buttons.extend([
            InlineKeyboardButton(text=tasks_label, callback_data=f"tm:m:t:{team_id}"),
            InlineKeyboardButton(text="📎 Файлы", callback_data=f"tm:m:f:{team_id}"),
        ])
    menu_buttons.append(InlineKeyboardButton(text="⚙️ Управление командой", callback_data=f"tm:m:g:{team_id}"))

    buttons = _rows(menu_buttons)
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_tasks_keyboard(
    team_id: str,
    columns: list[dict],
    my_tasks_callback: str,
    back_callback: str,
    col_callback_prefix: str = "tasks:col",
    pending_callback: str | None = None,
    pending_count: int = 0,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    buttons.append([InlineKeyboardButton(text="📥 Мои задачи", callback_data=my_tasks_callback)])
    if pending_callback:
        label = f"🆕 На подтверждение ({pending_count})" if pending_count else "🆕 На подтверждение"
        buttons.append([InlineKeyboardButton(text=label, callback_data=pending_callback)])
    for col in columns:
        title = (col.get("title") or "Колонка")[:_MAX_TITLE]
        buttons.append([InlineKeyboardButton(
            text=f"📌 {title}",
            callback_data=f"{col_callback_prefix}:{col['id']}:0",
        )])
    if not columns:
        buttons.append([InlineKeyboardButton(text="⚠️ Канбан-доска не настроена", callback_data="noop")])
    buttons.append([InlineKeyboardButton(text="← К команде", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_context_manager_files_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")],
        [InlineKeyboardButton(text="📋 Список файлов", callback_data=f"team_ctx:files_list:{team_id}")],
        [InlineKeyboardButton(text="← К команде", callback_data=f"team_ctx:manager:{team_id}")],
    ])


def team_context_manager_manage_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Участники", callback_data=f"team_ctx:members:{team_id}"),
            InlineKeyboardButton(text="🔗 Привязать чат", callback_data=f"team_ctx:link_chat:{team_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"team_ctx:update:{team_id}"),
            InlineKeyboardButton(text="🗑 Деактивировать", callback_data=f"team_ctx:deactivate:{team_id}"),
        ],
        [InlineKeyboardButton(text="🎯 YouGile", callback_data=f"team_ctx:yougile:{team_id}")],
        [InlineKeyboardButton(text="← К команде", callback_data=f"team_ctx:manager:{team_id}")],
    ])


def team_context_member_keyboard(team_id: str = "", has_chat: bool = True, has_kanban: bool = True) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if has_chat and team_id:
        tasks_label = "📋 Задачи" if has_kanban else "⚠️ Задачи (канбан не настроен)"
        buttons.extend(_rows([
            InlineKeyboardButton(text=tasks_label, callback_data=f"tm:u:t:{team_id}"),
            InlineKeyboardButton(text="📎 Файлы", callback_data=f"tm:u:f:{team_id}"),
        ]))
    buttons.append([InlineKeyboardButton(text="← Мои команды", callback_data="member:teams_overview")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)




def team_context_member_files_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить файл", callback_data=f"team_ctx:upload:{team_id}")],
        [InlineKeyboardButton(text="📋 Список файлов", callback_data=f"team_ctx:files_list:{team_id}")],
        [InlineKeyboardButton(text="← К команде", callback_data=f"team_ctx:member:{team_id}")],
    ])


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
