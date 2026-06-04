from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers.upload import UPLOAD_PROMPT_TEXT
from keyboards.member import back_to_member_keyboard, member_main_keyboard
from services.admin_service import get_user_by_telegram_id
from services.team_service import get_member_teams, get_my_teams
from states.upload import FileUploadStates

router = Router()

NO_TEAM_TEXT = (
    "Вы зарегистрированы, но пока не состоите ни в одной команде.\n"
    "Нужно, чтобы менеджер добавил вас в команду."
)


async def show_member_panel(message: Message, user: dict) -> None:
    member_teams, manager_teams = await asyncio.gather(
        get_member_teams(message.from_user.id),
        get_my_teams(message.from_user.id),
    )
    is_manager = bool(manager_teams)
    if not is_manager and not member_teams:
        await message.answer(NO_TEAM_TEXT)
        return

    await message.answer(
        _member_panel_text(user, is_manager=is_manager),
        reply_markup=member_main_keyboard(is_manager=is_manager),
    )


@router.callback_query(F.data == "member:back")
async def member_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user, member_teams, manager_teams = await asyncio.gather(
        get_user_by_telegram_id(callback.from_user.id),
        get_member_teams(callback.from_user.id),
        get_my_teams(callback.from_user.id),
    )
    is_manager = bool(manager_teams)
    if not is_manager and not member_teams:
        await callback.message.edit_text(NO_TEAM_TEXT)
        await callback.answer()
        return

    await callback.message.edit_text(
        _member_panel_text(user, is_manager=is_manager),
        reply_markup=member_main_keyboard(is_manager=is_manager),
    )
    await callback.answer()


@router.callback_query(F.data == "member:upload")
async def member_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FileUploadStates.waiting_for_file)
    await callback.message.answer(UPLOAD_PROMPT_TEXT)
    await callback.answer()


@router.callback_query(F.data == "member:help")
async def member_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>Помощь</b>\n\n"
        "/start — открыть панель участника\n"
        "/upload — загрузить аудио или видео\n"
        "/cancel — отменить текущее действие",
        reply_markup=back_to_member_keyboard(),
    )
    await callback.answer()


def _member_panel_text(user: dict | None = None, is_manager: bool = False) -> str:
    title = "Панель менеджера" if is_manager else "Панель участника"
    if not user:
        return f"<b>{title}</b>\n\nВыберите действие:"

    yougile = user.get("yougileDisplayName")
    if yougile:
        status = f"✅ Привязан к YouGile: <b>{yougile}</b>"
    else:
        status = "⚠️ YouGile аккаунт не привязан"
    manager_note = "\n\nДоступны действия менеджера команды." if is_manager else ""
    return f"<b>{title}</b>\n\nПривет! Ты зарегистрирован в системе.\n\n{status}{manager_note}\n\nВыберите действие:"
