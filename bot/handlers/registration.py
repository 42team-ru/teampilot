from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.auth import _handle_join, _handle_link
from handlers.member import show_member_panel
from services.admin_service import get_user_by_telegram_id, lookup_user_by_telegram_id
from services.backend_error import BackendApiError
from services.user_service import patch_telegram_login, register_user, update_user
from states.auth import RegistrationStates

router = Router()

REGISTRATION_PROMPT = (
    "Сначала нужно зарегистрироваться.\n"
    "Введите фамилию и имя одним сообщением. Например: <b>Петров Иван</b>"
)
REGISTRATION_INVALID_TEXT = (
    "Введите фамилию и имя через пробел. Например: <b>Петров Иван</b>"
)
REGISTRATION_DONE_TEXT = "Готово, данные сохранены."


class NeedsRegistration(BaseFilter):
    async def __call__(self, message: Message) -> bool | dict:
        if message.from_user is None or not message.text:
            return False

        try:
            result = await lookup_user_by_telegram_id(message.from_user.id)
        except BackendApiError:
            return {"existing_user": None, "lookup_failed": True}

        user = result.user
        if user is None:
            return {"existing_user": None, "lookup_failed": False}

        if _missing_name(user):
            return {"existing_user": user, "lookup_failed": False}

        return False


@router.message(
    StateFilter(
        RegistrationStates.waiting_for_full_name,
        RegistrationStates.waiting_for_first_name,
        RegistrationStates.waiting_for_last_name,
    ),
    Command("cancel"),
)
async def cancel_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Регистрация отменена. Чтобы пользоваться ботом, отправьте /start и введите фамилию и имя."
    )


@router.message(RegistrationStates.waiting_for_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    parsed_name = _parse_full_name(message.text or "")
    if parsed_name is None:
        await message.answer(REGISTRATION_INVALID_TEXT, parse_mode="HTML")
        return

    last_name, first_name = parsed_name
    await _finish_registration(
        message,
        state,
        first_name=first_name,
        last_name=last_name,
    )


@router.message(RegistrationStates.waiting_for_first_name, F.text)
async def process_first_name(message: Message, state: FSMContext) -> None:
    first_name = (message.text or "").strip()
    if not first_name or " " in first_name:
        await message.answer(
            "Введите только имя, одним словом. Например: <b>Иван</b>",
            parse_mode="HTML",
        )
        return
    await state.update_data(registration_first_name=first_name)
    await state.set_state(RegistrationStates.waiting_for_last_name)
    await message.answer(
        "Теперь введите фамилию. Например: <b>Петров</b>",
        parse_mode="HTML",
    )


@router.message(RegistrationStates.waiting_for_last_name, F.text)
async def process_last_name(message: Message, state: FSMContext) -> None:
    last_name = (message.text or "").strip()
    if not last_name or " " in last_name:
        await message.answer(
            "Введите только фамилию, одним словом. Например: <b>Петров</b>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    await _finish_registration(
        message,
        state,
        first_name=data.get("registration_first_name", ""),
        last_name=last_name,
    )


@router.message(F.chat.type == "private", F.text.startswith("/"), NeedsRegistration())
async def require_registration(
    message: Message,
    state: FSMContext,
    existing_user: dict | None,
    lookup_failed: bool = False,
) -> None:
    if lookup_failed:
        await message.answer(
            "Не могу проверить регистрацию: backend недоступен. Попробуйте позже."
        )
        return

    await start_registration(
        message,
        state,
        existing_user=existing_user,
        pending_command=message.text,
    )


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text.startswith("/"), NeedsRegistration())
async def require_registration_in_group(message: Message, lookup_failed: bool = False) -> None:
    if lookup_failed:
        await message.answer(
            "Не могу проверить регистрацию: backend недоступен. Попробуйте позже."
        )
        return

    bot_info = await message.bot.get_me()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Зарегистрироваться",
            url=f"https://t.me/{bot_info.username}?start=register",
        )
    ]])
    await message.answer(
        "Сначала зарегистрируйтесь в личке бота: введите фамилию и имя, потом повторите команду.",
        reply_markup=keyboard,
    )


async def start_registration(
    message: Message,
    state: FSMContext,
    *,
    existing_user: dict | None = None,
    pending_command: str | None = None,
) -> None:
    await state.update_data(
        registration_pending_command=pending_command,
        registration_user_id=existing_user.get("userId") if existing_user else None,
    )
    await state.set_state(RegistrationStates.waiting_for_full_name)
    await message.answer(REGISTRATION_PROMPT, parse_mode="HTML")


async def ensure_telegram_login(message: Message, user: dict) -> bool:
    """Check if user has telegramLogin; patch silently if possible, block if not.

    Returns True if the caller can proceed, False if blocked.
    """
    if user.get("telegramLogin"):
        return True

    tg_username = message.from_user.username if message.from_user else None

    if tg_username:
        await patch_telegram_login(
            user_id=user["userId"],
            telegram_id=message.from_user.id,
            telegram_login=tg_username,
        )
        return True

    await message.answer(
        "Для использования бота необходимо установить @username в настройках Telegram.\n"
        "После этого повторите команду."
    )
    return False


async def _finish_registration(
    message: Message,
    state: FSMContext,
    *,
    first_name: str,
    last_name: str,
) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    existing_user_id = data.get("registration_user_id")

    if existing_user_id:
        result = await update_user(
            user_id=existing_user_id,
            telegram_id=message.from_user.id,
            first_name=first_name,
            last_name=last_name,
            telegram_login=message.from_user.username,
        )
    else:
        result = await register_user(
            telegram_id=message.from_user.id,
            telegram_login=message.from_user.username,
            first_name=first_name,
            last_name=last_name,
        )

    user_info = {
        "userId": result.get("userId"),
        "telegramId": message.from_user.id,
        "firstName": first_name,
        "lastName": last_name,
        "telegramLogin": message.from_user.username,
        "systemRole": result.get("systemRole") or result.get("role", "USER"),
    }

    pending_command = data.get("registration_pending_command")
    await state.clear()
    await message.answer(REGISTRATION_DONE_TEXT)
    await _continue_after_registration(message, state, pending_command, user=user_info)


def _parse_full_name(text: str) -> tuple[str, str] | None:
    parts = [part.strip() for part in text.split() if part.strip()]
    if len(parts) < 2 or any(part.startswith("/") for part in parts):
        return None

    last_name = parts[0]
    first_name = " ".join(parts[1:])
    return last_name, first_name


def _missing_name(user: dict) -> bool:
    return not _filled(user.get("firstName")) or not _filled(user.get("lastName"))


def _filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


async def _continue_after_registration(
    message: Message,
    state: FSMContext,
    pending_command: str | None,
    user: dict | None = None,
) -> None:
    if not pending_command:
        resolved_user = user or await get_user_by_telegram_id(message.from_user.id)
        await show_member_panel(message, resolved_user or {})
        return

    parts = pending_command.split(maxsplit=1)
    command = parts[0].split("@", 1)[0].lower()
    payload = parts[1] if len(parts) > 1 else ""

    if command != "/start":
        await message.answer("Теперь можно повторить команду.")
        return

    if payload.startswith("join_"):
        await _handle_join(message, payload[len("join_"):])
        return

    if payload.startswith("link_"):
        await _handle_link(message, state, payload[len("link_"):])
        return

    if payload.startswith("setup_"):
        await message.answer("Теперь можно повторить ссылку настройки.")
        return

    resolved_user = user or await get_user_by_telegram_id(message.from_user.id)
    await show_member_panel(message, resolved_user or {})
