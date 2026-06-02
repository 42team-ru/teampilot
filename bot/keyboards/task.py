from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
