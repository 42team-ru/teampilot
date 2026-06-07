from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from services.profile_service import get_user_stats

router = Router()

_ALL_ACHIEVEMENTS = [
    {
        "key": "FIRST_STEP",
        "emoji": "🎯",
        "name": "Первый шаг",
        "description": "Первая выполненная задача",
        "xp": 50,
    },
    {
        "key": "LIGHTNING",
        "emoji": "⚡",
        "name": "Молния",
        "description": "Закрыть задачу быстрее половины отведенного времени",
        "xp": 100,
    },
    {
        "key": "EARLY_BIRD",
        "emoji": "🏃",
        "name": "Ранний финиш",
        "description": "Закрыть задачу минимум за 24 часа до дедлайна",
        "xp": 75,
    },
    {
        "key": "WEEK_STREAK",
        "emoji": "🔥",
        "name": "Неделя в огне",
        "description": "Держать стрик 7 дней",
        "xp": 100,
    },
    {
        "key": "SNIPER",
        "emoji": "🎯",
        "name": "Снайпер",
        "description": "10 задач подряд закрыть в срок",
        "xp": 150,
    },
    {
        "key": "MOUNTAIN",
        "emoji": "🏔️",
        "name": "Гора задач",
        "description": "Выполнить 50 задач",
        "xp": 200,
    },
    {
        "key": "CLEAN_MONTH",
        "emoji": "❄️",
        "name": "Чистый месяц",
        "description": "30 дней без просроченных задач",
        "xp": 200,
    },
]

_LEVELS = [
    (1, 0, "Новобранец"),
    (2, 400, "Исполнитель"),
    (3, 900, "Специалист"),
    (4, 1600, "Профессионал"),
    (5, 2500, "Эксперт"),
    (6, 3600, "Легенда"),
]


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    if message.from_user is None:
        return

    stats = await get_user_stats(message.from_user.id)
    await message.answer(
        _render_profile(stats),
        parse_mode="HTML",
        reply_markup=_profile_keyboard(),
    )


@router.callback_query(F.data == "profile:open")
@router.callback_query(F.data == "profile:refresh")
async def open_profile(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    stats = await get_user_stats(callback.from_user.id)
    try:
        await callback.message.edit_text(
            _render_profile(stats),
            parse_mode="HTML",
            reply_markup=_profile_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Обновлено" if callback.data == "profile:refresh" else "Профиль")


@router.callback_query(F.data == "profile:achievements")
async def show_achievements(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    stats = await get_user_stats(callback.from_user.id)
    try:
        await callback.message.edit_text(
            _render_achievements(stats),
            parse_mode="HTML",
            reply_markup=_achievements_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Готово")


@router.callback_query(F.data == "profile:all_achievements")
async def show_all_achievements(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    stats = await get_user_stats(callback.from_user.id)
    try:
        await callback.message.edit_text(
            _render_all_achievements(stats),
            parse_mode="HTML",
            reply_markup=_submenu_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Все достижения")


@router.callback_query(F.data == "profile:stats")
async def show_stats(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    stats = await get_user_stats(callback.from_user.id)
    try:
        await callback.message.edit_text(
            _render_stats(stats),
            parse_mode="HTML",
            reply_markup=_stats_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Статистика")


@router.callback_query(F.data == "profile:levels")
async def show_levels(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    stats = await get_user_stats(callback.from_user.id)
    try:
        await callback.message.edit_text(
            _render_levels(stats),
            parse_mode="HTML",
            reply_markup=_submenu_keyboard(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
    await callback.answer("Уровни")


def _render_profile(stats: dict) -> str:
    level = int(stats.get("level") or 1)
    level_name = escape(str(stats.get("levelName") or "Новобранец"))
    xp = int(stats.get("xp") or 0)
    xp_next = int(stats.get("xpForNextLevel") or 100)
    xp_cur = int(stats.get("xpForCurrentLevel") or 0)
    bar = _xp_bar(xp, xp_cur, xp_next)
    streak = int(stats.get("streakDays") or 0)
    completed = int(stats.get("completedCount") or 0)
    overdue = int(stats.get("overdueCount") or 0)
    on_time = round(float(stats.get("onTimeRate") or 0.0) * 100)

    return (
        "👤 <b>Профиль</b>\n\n"
        f"⭐ <b>Уровень {level} — {level_name}</b>\n"
        f"{bar}  {xp} / {xp_next} XP\n\n"
        f"✅ Выполнено: <b>{completed}</b>    ❌ Просрочено: <b>{overdue}</b>\n"
        f"📊 On-time: <b>{on_time}%</b>    🔥 Стрик: <b>{streak} дней</b>"
    )


def _render_achievements(stats: dict) -> str:
    achievements = stats.get("achievements") or []
    if not achievements:
        return (
            "🏆 <b>Мои достижения</b>\n\n"
            "Пока пусто. Закрой первую задачу в срок, и здесь появится награда."
        )

    lines = [f"🏆 <b>Мои достижения</b> ({len(achievements)}/{len(_ALL_ACHIEVEMENTS)})", ""]
    for achievement in achievements:
        emoji = escape(str(achievement.get("emoji") or "🏅"))
        name = escape(str(achievement.get("name") or achievement.get("key") or "Достижение"))
        awarded_at = str(achievement.get("awardedAt") or "")[:10]
        suffix = f" · {escape(awarded_at)}" if awarded_at else ""
        lines.append(f"{emoji} <b>{name}</b>{suffix}")
    return "\n".join(lines)


def _render_all_achievements(stats: dict) -> str:
    awarded_keys = {
        str(achievement.get("key"))
        for achievement in stats.get("achievements") or []
        if achievement.get("key")
    }
    lines = ["🎖 <b>Все достижения</b>", ""]
    for achievement in _ALL_ACHIEVEMENTS:
        unlocked = achievement["key"] in awarded_keys
        marker = "✅" if unlocked else "🔒"
        lines.append(
            f"{marker} {achievement['emoji']} <b>{escape(achievement['name'])}</b> "
            f"+{achievement['xp']} XP\n"
            f"   {escape(achievement['description'])}"
        )
    return "\n".join(lines)


def _render_stats(stats: dict) -> str:
    completed = int(stats.get("completedCount") or 0)
    overdue = int(stats.get("overdueCount") or 0)
    on_time_rate = float(stats.get("onTimeRate") or 0.0)
    on_time = max(0, completed - overdue)
    streak = int(stats.get("streakDays") or 0)
    xp = int(stats.get("xp") or 0)
    level = int(stats.get("level") or 1)
    level_name = escape(str(stats.get("levelName") or "Новобранец"))
    xp_cur = int(stats.get("xpForCurrentLevel") or 0)
    xp_next = int(stats.get("xpForNextLevel") or 100)
    achievements = stats.get("achievements") or []
    to_next = max(0, xp_next - xp)

    return (
        "📊 <b>Статистика</b>\n\n"
        f"✅ Выполнено задач: <b>{completed}</b>\n"
        f"🟢 В срок: <b>{on_time}</b>\n"
        f"❌ Просрочено: <b>{overdue}</b>\n"
        f"📈 On-time rate: <b>{round(on_time_rate * 100)}%</b>\n\n"
        f"⭐ Уровень: <b>{level} — {level_name}</b>\n"
        f"{_xp_bar(xp, xp_cur, xp_next)}  {xp} / {xp_next} XP\n"
        f"До следующего уровня: <b>{to_next} XP</b>\n\n"
        f"🔥 Стрик: <b>{streak} дней</b>\n"
        f"🏆 Достижения: <b>{len(achievements)}/{len(_ALL_ACHIEVEMENTS)}</b>"
    )


def _render_levels(stats: dict) -> str:
    current_level = int(stats.get("level") or 1)
    lines = ["⭐ <b>Уровни</b>", ""]
    for level, xp_from, name in _LEVELS:
        marker = "✅" if level <= current_level else "▫️"
        lines.append(f"{marker} <b>{level}. {escape(name)}</b> · от {xp_from} XP")
    return "\n".join(lines)


def _profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="profile:stats"),
            InlineKeyboardButton(text="🏆 Мои достижения", callback_data="profile:achievements"),
        ],
        [
            InlineKeyboardButton(text="🎖 Все достижения", callback_data="profile:all_achievements"),
            InlineKeyboardButton(text="⭐ Уровни", callback_data="profile:levels"),
        ],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="profile:refresh")],
        [
            InlineKeyboardButton(text="← Назад", callback_data="member:back"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back"),
        ],
    ])


def _achievements_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎖 Все достижения", callback_data="profile:all_achievements")],
        [
            InlineKeyboardButton(text="← Профиль", callback_data="profile:open"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back"),
        ],
    ])


def _stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Мои достижения", callback_data="profile:achievements"),
            InlineKeyboardButton(text="⭐ Уровни", callback_data="profile:levels"),
        ],
        [
            InlineKeyboardButton(text="← Профиль", callback_data="profile:open"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back"),
        ],
    ])


def _submenu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="profile:stats"),
            InlineKeyboardButton(text="🏆 Мои достижения", callback_data="profile:achievements"),
        ],
        [
            InlineKeyboardButton(text="← Профиль", callback_data="profile:open"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="member:back"),
        ],
    ])


def _xp_bar(xp: int, xp_cur: int, xp_next: int, width: int = 10) -> str:
    progress = (xp - xp_cur) / max(1, xp_next - xp_cur)
    progress = min(1.0, max(0.0, progress))
    filled = round(progress * width)
    return "█" * filled + "░" * (width - filled)
