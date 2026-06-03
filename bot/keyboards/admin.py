from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Создать команду", callback_data="admin:create_team")],
        [InlineKeyboardButton(text="🔗 Ссылка для вступления", callback_data="admin:get_invite")],
        [InlineKeyboardButton(text="💬 Добавить бота в чат", callback_data="admin:add_to_chat")],
        [InlineKeyboardButton(text="👥 Участники команды", callback_data="admin:team")],
    ])


def back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="admin:back")],
    ])


def skip_keyboard(skip_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data=skip_callback)],
        [InlineKeyboardButton(text="✖ Отмена", callback_data="admin:cancel_create_team")],
    ])
