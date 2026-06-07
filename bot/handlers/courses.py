from __future__ import annotations

from html import escape
from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.backend_error import BackendApiError
from services.course_service import add_course, list_courses
from services.team_service import get_my_teams
from states.courses import CoursesAddStates

router = Router()

_PAGE_SIZE = 5


def _normalize_course_url(value: str | None) -> str | None:
    url = (value or "").strip()
    if not url or len(url) > 2048 or any(char.isspace() for char in url):
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


async def _team_back_callback(team_id: str, telegram_id: int) -> str:
    try:
        manager_teams = await get_my_teams(telegram_id)
        if any(str(t.get("id")) == team_id for t in manager_teams):
            return f"team_ctx:manager:{team_id}"
    except Exception:
        pass
    return f"team_ctx:member:{team_id}"


def _back_to_team_keyboard(team_id: str, back_callback: str | None = None) -> InlineKeyboardMarkup:
    cb = back_callback or f"team_ctx:manager:{team_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад к команде", callback_data=cb)],
    ])


def _cancel_keyboard(team_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖ Отмена", callback_data=f"courses:cancel:{team_id}")],
    ])


@router.callback_query(F.data.startswith("courses:add:"))
async def courses_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    team_id = callback.data.split(":", 2)[2]
    await state.update_data(courses_team_id=team_id)
    await state.set_state(CoursesAddStates.waiting_for_url)
    await callback.message.edit_text(
        "Пришлите ссылку на курс (Skillbox, Степик, YouTube и т.д.):",
        reply_markup=_cancel_keyboard(team_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("courses:cancel:"))
async def courses_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    team_id = callback.data.split(":", 2)[2]
    await callback.message.edit_text(
        "Добавление курса отменено.",
        reply_markup=_back_to_team_keyboard(team_id),
    )
    await callback.answer()


@router.message(CoursesAddStates.waiting_for_url)
async def courses_add_url(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    team_id: str = data.get("courses_team_id", "")

    url = _normalize_course_url(message.text)
    if url is None:
        await message.answer(
            "Некорректная ссылка. Убедитесь, что ссылка начинается с http:// или https:// и не содержит пробелов.",
            reply_markup=_cancel_keyboard(team_id),
        )
        return

    back_cb = await _team_back_callback(team_id, message.from_user.id)

    try:
        course = await add_course(team_id, url, message.from_user.id)
    except BackendApiError as e:
        await message.answer(
            f"Не удалось добавить курс: {escape(e.detail or 'ошибка сервера')}",
            reply_markup=_back_to_team_keyboard(team_id, back_cb),
        )
        await state.clear()
        return

    await state.clear()

    title = escape(course.get("title") or url)
    description = course.get("description") or ""
    desc_preview = escape(description[:150]) if description else ""

    text = f"Курс добавлен: <b>{title}</b>"
    if desc_preview:
        text += f"\n{desc_preview}"

    await message.answer(
        text,
        reply_markup=_back_to_team_keyboard(team_id, back_cb),
    )


@router.callback_query(F.data.startswith("courses:list:"))
async def courses_list(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    team_id = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    back_cb = await _team_back_callback(team_id, callback.from_user.id)

    try:
        courses = await list_courses(team_id, callback.from_user.id)
    except BackendApiError as e:
        await callback.answer(f"Ошибка: {e.detail or 'недоступно'}", show_alert=True)
        return

    if not courses:
        await callback.message.edit_text(
            "В команде пока нет курсов.",
            reply_markup=_back_to_team_keyboard(team_id, back_cb),
        )
        await callback.answer()
        return

    total = len(courses)
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * _PAGE_SIZE
    page_courses = courses[start: start + _PAGE_SIZE]

    lines = [f"<b>Курсы команды</b> (стр. {page + 1}/{total_pages}):", ""]
    for i, c in enumerate(page_courses, start + 1):
        title = escape(c.get("title") or "Без названия")
        description = c.get("description") or ""
        desc_preview = escape(description[:80]) if description else ""
        scope = " [global]" if c.get("scope") == "GLOBAL" else ""
        lines.append(f"{i}. <b>{title}</b>{scope}")
        if desc_preview:
            lines.append(f"   {desc_preview}")

    rows: list[list[InlineKeyboardButton]] = []
    for c in page_courses:
        url = c.get("url") or ""
        title_short = (c.get("title") or "Открыть")[:40]
        if url:
            rows.append([InlineKeyboardButton(text=f"🔗 {title_short}", url=url)])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"courses:list:{team_id}:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"courses:list:{team_id}:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="← Назад", callback_data=back_cb)])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()
