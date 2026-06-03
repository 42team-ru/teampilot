from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def member_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить файл", callback_data="member:upload")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="member:help")],
    ])


def back_to_member_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="member:back")],
    ])
