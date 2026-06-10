from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.backend_error import BackendApiError
from services.payment_service import initiate_team_payment
from states.payment import TeamCreateStates

router = Router()

_PRICE_DISPLAY = "2500 ₽"
_MAX_NAME_LEN = 100


def _payment_confirm_keyboard(team_name: str) -> InlineKeyboardMarkup:
    safe = team_name[:_MAX_NAME_LEN]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Перейти к оплате", callback_data=f"team_pay:confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="team_pay:cancel")],
    ])


def _payment_link_keyboard(confirmation_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {_PRICE_DISPLAY}", url=confirmation_url)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")],
    ])


@router.callback_query(F.data == "team:create")
async def handle_create_team_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TeamCreateStates.waiting_name)
    await callback.message.edit_text(
        "✏️ <b>Создание команды</b>\n\n"
        "Введите название команды (2–100 символов):\n\n"
        "<i>Для отмены нажмите /cancel</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="team_pay:cancel")]
        ]),
    )
    await callback.answer()


@router.message(TeamCreateStates.waiting_name, F.chat.type == "private", F.text)
async def handle_team_name_received(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text.startswith("/"):
        await state.clear()
        await message.answer("Создание команды отменено.")
        return

    if len(text) < 2 or len(text) > _MAX_NAME_LEN:
        await message.answer(
            f"Название должно быть от 2 до {_MAX_NAME_LEN} символов. Попробуйте ещё раз:"
        )
        return

    await state.update_data(team_name=text)

    await message.answer(
        f"📋 <b>Создание команды «{escape(text)}»</b>\n\n"
        f"💳 Стоимость: <b>{_PRICE_DISPLAY}</b> (тестовый платёж)\n\n"
        f"После оплаты вы станете менеджером команды и сможете:\n"
        f"• Добавлять участников\n"
        f"• Создавать задачи\n"
        f"• Привязать Telegram-группу\n",
        parse_mode="HTML",
        reply_markup=_payment_confirm_keyboard(text),
    )


@router.callback_query(F.data == "team_pay:confirm")
async def handle_team_payment_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    team_name = data.get("team_name")

    if not team_name:
        await callback.answer("Сессия истекла. Начните заново.", show_alert=True)
        await state.clear()
        return

    await callback.answer()
    await callback.message.edit_text(
        "⏳ Создаём платёж...",
        parse_mode="HTML",
    )

    try:
        result = await initiate_team_payment(callback.from_user.id, team_name)
    except BackendApiError as e:
        await callback.message.edit_text(
            f"❌ Не удалось создать платёж: {escape(e.user_message())}\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")]
            ]),
        )
        await state.clear()
        return

    confirmation_url = result.get("confirmationUrl")
    amount = result.get("amount", "100.00")
    is_test = result.get("test", True)

    test_note = " (тестовый режим)" if is_test else ""
    await state.clear()

    await callback.message.edit_text(
        f"⏳ <b>Платёж создан!</b>\n\n"
        f"Нажмите кнопку ниже, чтобы оплатить {escape(amount)} ₽{test_note}.\n\n"
        f"После оплаты команда <b>«{escape(team_name)}»</b> будет создана автоматически "
        f"и вы получите уведомление в бот.",
        parse_mode="HTML",
        reply_markup=_payment_link_keyboard(confirmation_url),
    )


@router.callback_query(F.data == "team_pay:cancel")
async def handle_team_payment_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Создание команды отменено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back")]
        ]),
    )
    await callback.answer()
