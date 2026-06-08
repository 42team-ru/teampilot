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
    home_keyboard,
    member_main_keyboard,
    my_tasks_team_keyboard,
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
from services.admin_service import get_user_by_telegram_id
from services.backend_error import BackendApiError
from services.task_service import get_tasks_page
from services.team_service import get_member_teams, get_my_teams, get_team_files, update_yougile_profile
from states.auth import UpdateYouGileStates

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
            has_kanban=bool(kanban),
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
    kanban = team.get("kanbanId")

    lines = [
        f"👤 <b>{escape(title)}</b>",
        "",
        f"Telegram чат: {'привязан' if chat_id else 'не привязан'}",
        f"Канбан: {'настроен' if kanban else '⚠️ не настроен'}",
        "",
        "Доступные действия собраны в блоках ниже.",
    ]
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=team_context_member_keyboard(team_id, has_chat=bool(chat_id), has_kanban=bool(kanban)),
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

    columns, pending_count = await asyncio.gather(
        get_team_columns(int(chat_id), callback.from_user.id),
        _pending_tasks_count(chat_id, callback.from_user.id),
    )
    note = "Выберите колонку или раздел:" if columns else "⚠️ Канбан-доска не настроена.\nДоступны только личные задачи."
    await callback.message.edit_text(
        f"📋 <b>Задачи: {escape(team.get('chatTitle') or team_id)}</b>\n\n{note}",
        reply_markup=team_tasks_keyboard(
            team_id,
            columns,
            my_tasks_callback=f"tasks:team_my:{team_id}:active:0",
            back_callback=f"team_ctx:manager:{team_id}",
            pending_callback=f"mgr:pending:{team_id}:0",
            pending_count=pending_count,
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


@router.callback_query(F.data.startswith("team_ctx:yougile:"))
async def team_ctx_yougile(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 2)[2]
    team = await _get_manager_team(callback.from_user.id, team_id)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return

    chat_id = team.get("telegramChatId")
    kanban = team.get("kanbanId")
    yougile = team.get("yougileToken") or team.get("yougileApiKey")
    title = team.get("chatTitle") or team_id

    lines = [
        f"🎯 <b>YouGile: {escape(title)}</b>",
        "",
        f"Канбан-доска: {'✅ настроена (<code>' + escape(str(kanban)) + '</code>)' if kanban else '⚠️ не настроена'}",
        f"Интеграция: {'✅ активна' if kanban else '❌ не подключена'}",
    ]
    if not chat_id:
        lines += ["", "⚠️ Подключение канбан-доски доступно только после привязки Telegram-чата к команде."]

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    if chat_id:
        rows.append([InlineKeyboardButton(text="⚙️ Привязать / настроить YouGile", callback_data=f"manager:setup_yougile:{chat_id}")])
    rows.append([InlineKeyboardButton(text="← Управление командой", callback_data=f"tm:m:g:{team_id}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard)
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


async def _show_my_tasks_team(callback: CallbackQuery, team: dict) -> None:
    team_id = str(team.get("id"))
    chat_id = team.get("telegramChatId")
    title = escape(team.get("chatTitle") or team_id)

    columns = await get_team_columns(int(chat_id), callback.from_user.id) if chat_id else []
    note = "Выберите колонку:" if columns else "⚠️ Канбан-доска не настроена.\nДоступны только личные задачи."

    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(callback.from_user.id),
        get_member_teams(callback.from_user.id),
    )
    back_cb = "member:back" if len(manager_teams + member_teams) == 1 else "member:mytasks"

    await callback.message.edit_text(
        f"📥 <b>Мои задачи: {title}</b>\n\n{note}",
        reply_markup=team_tasks_keyboard(
            team_id,
            columns,
            my_tasks_callback=f"tasks:team_my:{team_id}:active:0",
            back_callback=back_cb,
            col_callback_prefix="tasks:mc",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mytasks:t:"))
async def my_tasks_team(callback: CallbackQuery) -> None:
    team_id = callback.data.split(":", 2)[2]
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(callback.from_user.id),
        get_member_teams(callback.from_user.id),
    )
    all_teams = manager_teams + member_teams
    team = next((t for t in all_teams if str(t.get("id")) == team_id), None)
    if team is None:
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    await _show_my_tasks_team(callback, team)


@router.callback_query(F.data == "member:mytasks")
async def member_mytasks(callback: CallbackQuery) -> None:
    manager_teams, member_teams = await asyncio.gather(
        get_my_teams(callback.from_user.id),
        get_member_teams(callback.from_user.id),
    )
    all_teams = manager_teams + member_teams
    if not all_teams:
        await callback.message.edit_text(
            "У вас нет команд. Попросите менеджера добавить вас в команду.",
            reply_markup=home_keyboard(),
        )
        await callback.answer()
        return

    if len(all_teams) == 1:
        await _show_my_tasks_team(callback, all_teams[0])
        return

    await callback.message.edit_text(
        "📥 <b>Мои задачи</b>\n\nВыберите команду:",
        reply_markup=my_tasks_team_keyboard(manager_teams, member_teams),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("team_ctx:files_list:"))
async def team_ctx_files_list(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    team_id = callback.data.split(":", 2)[2]

    try:
        files = await get_team_files(team_id, callback.from_user.id)
    except Exception:
        await callback.answer("Не удалось загрузить список файлов.", show_alert=True)
        return

    back_button = [InlineKeyboardButton(text="← Назад", callback_data="member:back")]

    if not files:
        await callback.message.edit_text(
            "📂 <b>Файлы команды</b>\n\nФайлов пока нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_button]),
        )
        await callback.answer()
        return

    rows = []
    for idx, f in enumerate(files):
        label = f.get("title") or f.get("originalFilename") or "Файл"
        icon = "🎙" if (f.get("contentType") or "").startswith("audio") else "🎬"
        # callback_data limit = 64 bytes; use index instead of UUID
        rows.append([InlineKeyboardButton(
            text=f"{icon} {escape(label[:40])}",
            callback_data=f"fd:{team_id}:{idx}",
        )])
    rows.append(back_button)

    await callback.message.edit_text(
        "📂 <b>Файлы команды</b>\n\nВыберите файл для просмотра подробной информации:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fd:"))
async def file_detail_by_index(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    parts = callback.data.split(":", 2)
    team_id, idx_str = parts[1], parts[2]

    try:
        files = await get_team_files(team_id, callback.from_user.id)
    except Exception:
        await callback.answer("Не удалось загрузить файл.", show_alert=True)
        return

    try:
        f = files[int(idx_str)]
    except (IndexError, ValueError):
        f = None

    await _show_file_detail(callback, team_id, f)


async def _show_file_detail(callback, team_id: str, f) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if f is None:
        await callback.answer("Файл не найден.", show_alert=True)
        return

    title = f.get("title") or f.get("originalFilename") or "Без названия"
    description = f.get("description") or ""
    summary = f.get("summary") or ""
    download_url = f.get("downloadUrl") or ""
    content_type = f.get("contentType") or ""
    size_bytes = f.get("sizeBytes")

    lines = [f"📄 <b>{escape(title)}</b>"]
    if f.get("originalFilename") and f.get("title"):
        lines.append(f"<i>Файл: {escape(f['originalFilename'])}</i>")
    if content_type:
        lines.append(f"Тип: <code>{escape(content_type)}</code>")
    if size_bytes:
        lines.append(f"Размер: {size_bytes // 1024} КБ")
    if description:
        lines.append(f"\n📝 <b>Описание</b>\n{escape(description)}")
    if summary:
        lines.append(f"\n📋 <b>Резюме встречи</b>\n{escape(summary)}")
    if not description and not summary:
        lines.append("\n<i>AI-анализ ещё не готов — обработка аудио занимает время.</i>")
    if download_url:
        lines.append(f"\n⬇️ <a href=\"{download_url}\">Скачать файл</a>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← К списку файлов", callback_data=f"team_ctx:files_list:{team_id}")],
        ]),
        disable_web_page_preview=True,
    )
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



@router.callback_query(F.data.startswith("team_ctx:member_yougile:"))
async def team_ctx_member_yougile(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    await state.update_data(update_yougile_team_id=team_id)
    await state.set_state(UpdateYouGileStates.waiting_for_yougile_login)
    await callback.message.answer(
        "Введи <b>логин</b> от YouGile-аккаунта:\n\n/cancel — отменить",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(UpdateYouGileStates.waiting_for_yougile_login, F.text)
async def process_update_yougile_login(message: Message, state: FSMContext) -> None:
    login = (message.text or "").strip()
    if not login:
        await message.answer("Пришли логин от YouGile текстом.")
        return
    await state.update_data(update_yougile_login=login)
    await state.set_state(UpdateYouGileStates.waiting_for_yougile_password)
    await message.answer("Теперь введи <b>пароль</b> от YouGile:", parse_mode="HTML")


@router.message(UpdateYouGileStates.waiting_for_yougile_password, F.text)
async def process_update_yougile_password(message: Message, state: FSMContext) -> None:
    password = (message.text or "").strip()
    if not password:
        await message.answer("Пришли пароль YouGile текстом.")
        return

    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    team_id: str = data["update_yougile_team_id"]
    login: str = data["update_yougile_login"]
    await state.clear()

    checking_msg = await message.answer("⏳ Обновляю данные YouGile...")

    try:
        await update_yougile_profile(team_id, login, password, message.from_user.id)
    except BackendApiError as e:
        await checking_msg.edit_text(
            f"❌ Не удалось обновить данные.\n{e.user_message()}\n\nПроверь логин/пароль и попробуй снова."
        )
        return

    await checking_msg.edit_text(
        "✅ YouGile-профиль обновлён!\n\n"
        "Задачи теперь будут назначаться на тебя.",
        reply_markup=home_keyboard(),
    )


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
        pending_approval=True,
        page=0,
        size=1,
    )
    return int(page.get("totalElements") or len(page.get("content", [])))
