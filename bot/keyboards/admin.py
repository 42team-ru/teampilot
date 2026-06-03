from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📧 Пригласить участника", callback_data="admin:invite")],
        [InlineKeyboardButton(text="💬 Добавить бота в чат", callback_data="admin:add_to_chat")],
        [InlineKeyboardButton(text="👥 Участники команды", callback_data="admin:team")],
    ])


def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="admin:back")],
    ])
