from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger

from kafka.consumer import _summary_members_cache
from keyboards.sync import build_sync_member_keyboard, build_sync_summary_keyboard
from models.events import SyncMemberSummary

router = Router()

_STATUS_LABELS = {
    "AWAITING": "⏳ не отчитался",
    "CONFIRMED": "✅ отчитался",
    "EXCUSED": "🤒 на больничном/в отпуске",
}


@router.callback_query(F.data == "syncsum:noop")
async def syncsum_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("syncsum:"))
async def syncsum_navigate(callback: CallbackQuery) -> None:
    parts = callback.data.split(":", 2)
    team_id = parts[1]
    target = parts[2] if len(parts) > 2 else "0"

    cached = _summary_members_cache.get(team_id)
    if cached is None:
        await callback.message.edit_text(
            "Данные устарели, дождитесь следующей синхронизации.",
            reply_markup=None,
        )
        await callback.answer()
        return

    members: list[SyncMemberSummary] = cached["members"]
    if not members:
        await callback.message.edit_text(
            "Данные устарели, дождитесь следующей синхронизации.",
            reply_markup=None,
        )
        await callback.answer()
        return

    if target == "back":
        await callback.message.edit_text(
            cached["overview"],
            reply_markup=build_sync_summary_keyboard(team_id),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    try:
        index = int(target)
    except ValueError:
        index = 0

    total = len(members)
    index = max(0, min(index, total - 1))

    member = members[index]
    text = _format_member_card(member, index, total)
    await callback.message.edit_text(
        text,
        reply_markup=build_sync_member_keyboard(team_id, index, total),
        parse_mode="HTML",
    )
    await callback.answer()


def _format_member_card(member: SyncMemberSummary, index: int, total: int) -> str:
    username = escape(member.username or "Без имени")
    lines = [f"👤 <b>{username}</b> ({index + 1}/{total})", ""]

    status_label = _STATUS_LABELS.get(member.status or "", member.status or "неизвестно")
    lines.append(f"Статус: {status_label}")
    if member.status == "EXCUSED" and member.excuse_reason:
        lines.append(f"Причина: {escape(member.excuse_reason)}")

    has_content = False

    if member.confirmed_tasks:
        has_content = True
        lines.append("")
        lines.append("✅ Закрыл задачи:")
        for title in member.confirmed_tasks:
            lines.append(f"  • {escape(title)}")

    if member.pending_tasks:
        has_content = True
        lines.append("")
        lines.append("🆕 Новые задачи:")
        for title in member.pending_tasks:
            lines.append(f"  • {escape(title)}")

    if member.raw_text:
        has_content = True
        lines.append("")
        lines.append("📝 Отчёт:")
        lines.append(escape(member.raw_text))

    if not has_content:
        lines.append("")
        lines.append("Нет данных за сегодня.")

    return "\n".join(lines)
