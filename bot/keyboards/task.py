from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE_LEN = 30
_MAX_PROJECTS = 8


def build_projects_keyboard(projects: list[dict]) -> InlineKeyboardMarkup:
    """projects: [{"id": str, "title": str}, ...]. Max 8 items shown."""
    buttons = []
    for project in projects[:_MAX_PROJECTS]:
        title = project["title"][:_MAX_TITLE_LEN]
        buttons.append([InlineKeyboardButton(
            text=f"📋 {title}",
            callback_data=f"select_board:{project['id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_task_keyboard(proposal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Создать", callback_data=f"task_confirm:{proposal_id}"),
        InlineKeyboardButton(text="❌ Пропустить", callback_data=f"task_reject:{proposal_id}"),
    ]])


def build_status_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 В работе", callback_data=f"status:{task_id}:in_progress")],
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"status:{task_id}:done")],
        [InlineKeyboardButton(text="🚫 Заблокировано", callback_data=f"status:{task_id}:blocked")],
    ])
