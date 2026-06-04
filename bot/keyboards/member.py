from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def member_main_keyboard(is_manager: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if is_manager:
        buttons.extend([
            [InlineKeyboardButton(text="👥 Мои команды", callback_data="manager:teams")],
            [InlineKeyboardButton(text="👤 Участники команды", callback_data="manager:members")],
            [InlineKeyboardButton(text="🔗 Привязать чат", callback_data="manager:link_chat")],
            [InlineKeyboardButton(text="✏️ Обновить команду", callback_data="manager:update")],
            [InlineKeyboardButton(text="🗑 Деактивировать команду", callback_data="manager:deactivate")],
        ])

    buttons.extend([
        [InlineKeyboardButton(text="📤 Загрузить файл", callback_data="member:upload")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="member:help")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_member_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="member:back")],
    ])
