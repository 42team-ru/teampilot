from __future__ import annotations

import asyncio
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.member import (
    back_to_member_keyboard,
    back_to_teams_keyboard,
    member_main_keyboard,
    team_context_manager_keyboard,
    team_context_manager_files_keyboard,
    team_context_manager_manage_keyboard,
    team_context_member_keyboard,
    team_context_member_files_keyboard,
    team_overview_keyboard,
    team_tasks_keyboard,
    upload_waiting_keyboard,
)
from services.task_service import get_team_columns
from handlers.tasks_commands import _render_my_tasks
from services.admin_service import get_user_by_telegram_id
from services.task_service import get_tasks_page
from services.team_service import get_member_teams, get_my_teams

router = Router()

NO_TEAM_TEXT = (
    "Вы зарегистрированы, но пока не состоите ни в одной команде.\n"
    "Нужно, чтобы менеджер добавил вас в команду."
)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


async def show_member_panel(message: Message, user: dict) -> None:
    member_teams, manager_teams = await asyncio.gather(
        get_member_teams(message.from_user.id),
        get_my_teams(message.from_user.id),
    )
    if not manager_teams and not member_teams:
        await message.answer(NO_TEAM_TEXT)
        return

    await message.answer(
        _member_panel_text(user, manager_teams=manager_teams, member_teams=member_teams),
        reply_markup=member_main_keyboard(),
    )


@router.callback_query(F.data == "member:back")
async def member_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user, member_teams, manager_teams = await asyncio.gather(
        get_user_by_telegram_id(callback.from_user.id),
        get_member_teams(callback.from_user.id),
        get_my_teams(callback.from_user.id),
    )
    if not manager_teams and not member_teams:
        await callback.message.edit_text(NO_TEAM_TEXT)
        await callback.answer()
        return

    await callback.message.edit_text(
        _member_panel_text(user, manager_teams=manager_teams, member_teams=member_teams),
        reply_markup=member_main_keyboard(),
    )
    await callback.answer()



@router.callback_query(F.data == "member:teams_overview")
async def member_teams_overview(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(callback.from_user.id),
        get_member_teams(callback.from_user.id),
    )

    if not manager_teams and not member_teams:
        await callback.message.edit_text(
            "Вы пока не состоите ни в одной команде.\n"
            "Нужно, чтобы менеджер добавил вас в команду.",
            reply_markup=back_to_member_keyboard(),
        )
        await callback.answer()
        return

    lines = ["<b>Мои команды</b>\n"]
    if manager_teams:
        lines.append("🔑 <b>Вы менеджер:</b>")
        for t in manager_teams:
            lines.append(f"  · {escape(t.get('chatTitle') or t.get('id') or '—')}")
    if member_teams:
        if manager_teams:
            lines.append("")
        lines.append("👤 <b>Вы участник:</b>")
        for t in member_teams:
            lines.append(f"  · {escape(t.get('chatTitle') or t.get('id') or '—')}")
    lines.append("\nВыберите команду:")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=team_overview_keyboard(manager_teams, member_teams),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:manager:"))
async def team_ctx_manager(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    teams = await get_my_teams(callback.from_user.id)
    team = next((t for t in teams if str(t.get("id")) == team_id), None)

    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или у вас нет прав менеджера.",
            reply_markup=back_to_teams_keyboard(),
        )
        await callback.answer()
        return

    title = team.get("chatTitle") or team_id
    chat_id = team.get("telegramChatId")
    kanban = team.get("kanbanId")
    active = "✅ активна" if team.get("active", True) else "⛔ неактивна"
    pending_count = await _pending_tasks_count(chat_id, callback.from_user.id) if chat_id else None

    lines = [
        f"🔑 <b>{escape(title)}</b>",
        "",
        f"Статус: {active}",
        f"Telegram чат: {'привязан' if chat_id else '⚠️ не привязан'}",
        f"Канбан: {'настроен' if kanban else '⚠️ не настроен'}",
        "",
        "Выберите действие:",
    ]
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=team_context_manager_keyboard(
            team_id,
            has_chat=bool(chat_id),
            pending_count=pending_count,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:member:"))
async def team_ctx_member(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 2)[2]
    teams = await get_member_teams(callback.from_user.id)
    team = next((t for t in teams if str(t.get("id")) == team_id), None)

    if team is None:
        await callback.message.edit_text(
            "Команда не найдена или вы не состоите в ней.",
            reply_markup=back_to_teams_keyboard(),
        )
        await callback.answer()
        return

    title = team.get("chatTitle") or team_id
    chat_id = team.get("telegramChatId")

    lines = [
        f"👤 <b>{escape(title)}</b>",
        "",
        f"Telegram чат: {'привязан' if chat_id else 'не привязан'}",
        "",
        "Доступные действия собраны в блоках ниже.",
    ]
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=team_context_member_keyboard(team_id, has_chat=bool(chat_id)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tm:m:t:"))
async def team_manager_tasks_menu(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 3)[3]
    team = await _get_manager_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return

    chat_id = team.get("telegramChatId")
    if not chat_id:
        await callback.answer("Сначала привяжите Telegram-чат к команде.", show_alert=True)
        return

    columns = await get_team_columns(int(chat_id), callback.from_user.id)
    note = "Выберите колонку или раздел:" if columns else "⚠️ Канбан-доска не настроена.\nДоступны только личные задачи."
    await callback.message.edit_text(
        f"📋 <b>Задачи: {escape(team.get('chatTitle') or team_id)}</b>\n\n{note}",
        reply_markup=team_tasks_keyboard(
            team_id,
            columns,
            my_tasks_callback=f"tasks:team_my:{team_id}:active:0",
            back_callback=f"team_ctx:manager:{team_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tm:m:f:"))
async def team_manager_files_menu(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 3)[3]
    team = await _get_manager_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    if not team.get("telegramChatId"):
        await callback.answer("Сначала привяжите Telegram-чат к команде.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📎 <b>Файлы: {escape(team.get('chatTitle') or team_id)}</b>\n\nЗдесь можно загрузить файл в чат команды.",
        reply_markup=team_context_manager_files_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tm:m:g:"))
async def team_manager_manage_menu(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 3)[3]
    team = await _get_manager_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⚙️ <b>Управление командой: {escape(team.get('chatTitle') or team_id)}</b>\n\n"
        "Выберите, что нужно изменить:",
        reply_markup=team_context_manager_manage_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tm:u:t:"))
async def team_member_tasks_menu(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 3)[3]
    team = await _get_member_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    if not team.get("telegramChatId"):
        await callback.answer("У команды пока нет привязанного Telegram-чата.", show_alert=True)
        return

    chat_id = int(team["telegramChatId"])
    columns = await get_team_columns(chat_id, callback.from_user.id)
    note = "Выберите колонку:" if columns else "⚠️ Канбан-доска не настроена.\nДоступны только личные задачи."
    await callback.message.edit_text(
        f"📋 <b>Задачи: {escape(team.get('chatTitle') or team_id)}</b>\n\n{note}",
        reply_markup=team_tasks_keyboard(
            team_id,
            columns,
            my_tasks_callback=f"tasks:team_my:{team_id}:active:0",
            back_callback=f"team_ctx:member:{team_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tm:u:f:"))
async def team_member_files_menu(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 3)[3]
    team = await _get_member_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    if not team.get("telegramChatId"):
        await callback.answer("У команды пока нет привязанного Telegram-чата.", show_alert=True)
        return

    await callback.message.edit_text(
        f"📎 <b>Файлы: {escape(team.get('chatTitle') or team_id)}</b>\n\nЗдесь можно загрузить файл в чат команды.",
        reply_markup=team_context_member_files_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data == "member:mytasks")
async def member_mytasks(callback: CallbackQuery) -> None:
    text, keyboard = await _render_my_tasks(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:upload:"))
async def team_ctx_upload(callback: CallbackQuery, state: FSMContext) -> None:
    from states.upload import FileUploadStates
    team_id = callback.data.split(":", 2)[2]

    # Find team in both managed and member lists
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(callback.from_user.id),
        get_member_teams(callback.from_user.id),
    )
    all_teams = {str(t.get("id")): t for t in (manager_teams + member_teams)}
    team = all_teams.get(team_id)

    if team is None:
        await callback.answer("Команда не найдена.", show_alert=True)
        return

    chat_id = team.get("telegramChatId")
    if not chat_id:
        await callback.answer(
            "У команды ещё нет привязанного Telegram-чата.\n"
            "Менеджер должен сначала привязать чат к команде.",
            show_alert=True,
        )
        return

    team_title = team.get("chatTitle") or team_id
    await state.update_data(upload_team_chat_id=int(chat_id))
    await state.set_state(FileUploadStates.waiting_for_file)
    await callback.message.answer(
        f"📤 Загрузка файла для команды <b>{escape(team_title)}</b>\n\n"
        "Отправьте аудио или видео. Поддерживаемые типы: аудио, голосовое, видео, видеосообщение.\n"
        "Отменить загрузку можно кнопкой ниже.",
        reply_markup=upload_waiting_keyboard(),
    )
    await callback.answer()



def _member_panel_text(
    user: dict | None = None,
    *,
    manager_teams: list[dict] | None = None,
    member_teams: list[dict] | None = None,
) -> str:
    managed = manager_teams or []
    member = member_teams or []

    name = ""
    if user:
        parts = []
        if user.get("firstName"):
            parts.append(user["firstName"])
        if user.get("lastName"):
            parts.append(user["lastName"])
        name = " ".join(parts)

    greeting = f"Привет, <b>{escape(name)}</b>!" if name else "Привет!"

    lines = ["<b>Главное меню</b>", "", greeting, ""]

    if managed:
        lines.append(f"🔑 Менеджер в {len(managed)} команд(е)")
    if member:
        lines.append(f"👤 Участник в {len(member)} команд(е)")
    if not managed and not member:
        lines.append("Вы пока не состоите в командах.")

    if user:
        yougile = user.get("yougileDisplayName")
        if yougile:
            lines.append(f"✅ YouGile: <b>{escape(yougile)}</b>")

    lines.append("")
    lines.append("Выберите действие:")
    return "\n".join(lines)


async def _get_manager_team(telegram_id: int, team_id: str) -> dict | None:
    teams = await get_my_teams(telegram_id)
    return next((team for team in teams if str(team.get("id")) == team_id), None)


async def _get_member_team(telegram_id: int, team_id: str) -> dict | None:
    teams = await get_member_teams(telegram_id)
    return next((team for team in teams if str(team.get("id")) == team_id), None)


async def _pending_tasks_count(chat_id: int | str, telegram_id: int) -> int:
    page = await get_tasks_page(
        chat_id=int(chat_id),
        telegram_id=telegram_id,
        completed=False,
        page=0,
        size=1,
    )
    return int(page.get("totalElements") or len(page.get("content", [])))
