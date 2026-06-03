from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers.upload import UPLOAD_PROMPT_TEXT
from keyboards.member import back_to_member_keyboard, member_main_keyboard
from states.upload import FileUploadStates

router = Router()


async def show_member_panel(message: Message, user: dict) -> None:
    await message.answer(
        _member_panel_text(user),
        reply_markup=member_main_keyboard(),
    )


@router.callback_query(F.data == "member:back")
async def member_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        _member_panel_text(),
        reply_markup=member_main_keyboard(),
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


def _member_panel_text(user: dict | None = None) -> str:
    if not user:
        return "<b>Панель участника</b>\n\nВыберите действие:"

    yougile = user.get("yougileDisplayName")
    if yougile:
        status = f"✅ Привязан к YouGile: <b>{yougile}</b>"
    else:
        status = "⚠️ YouGile аккаунт не привязан"
    return f"Привет! Ты зарегистрирован в системе.\n\n{status}\n\nВыберите действие:"
