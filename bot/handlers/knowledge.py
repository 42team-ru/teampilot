from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from services.knowledge_service import search_knowledge
from services.team_service import get_member_teams, get_team_id

router = Router()

_TYPE_ICON = {
    "meeting_summary": "📝",
    "file_summary": "📄",
    "decision": "✅",
    "task_archive": "📌",
}
_TYPE_LABEL = {
    "meeting_summary": "Саммари митинга",
    "file_summary": "Саммари файла",
    "decision": "Решение команды",
    "task_archive": "Архив задачи",
}
_EMPTY_QUERY_HINT = "Укажи запрос: <code>/wiki что решили по деплою</code>"
_NO_TEAM_MSG = "Эта команда недоступна здесь. Используй /wiki в групповом чате команды."
_NO_RESULTS_TPL = "По запросу «{q}» ничего не найдено в базе знаний команды."
_MIN_SCORE = 0.30
_CONTENT_LIMIT = 120


def _extract_query(message: Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _format_item(item: dict) -> str:
    kind = item.get("type", "")
    icon = _TYPE_ICON.get(kind, "ℹ️")
    label = _TYPE_LABEL.get(kind, kind)
    title = item.get("title", "")
    content = item.get("content", "")

    header = f"{icon} <b>{escape(label)}</b>" + (f" — {escape(title)}" if title else "")
    if kind == "task_archive" or not content:
        return header
    short = content if len(content) <= _CONTENT_LIMIT else content[:_CONTENT_LIMIT - 1].rstrip() + "…"
    return f"{header}\n{escape(short)}"


def _format_results(items: list[dict], query: str = "") -> str:
    relevant = [i for i in items if float(i.get("score", 0)) >= _MIN_SCORE]
    logger.debug(
        "wiki filter query={!r} total={} passed={} scores=[{}]",
        query[:60],
        len(items),
        len(relevant),
        ", ".join(f"{i.get('type','?')}:{float(i.get('score',0)):.3f}" for i in items),
    )
    if not relevant:
        return ""
    lines = ["<b>База знаний команды:</b>"]
    lines.extend(_format_item(i) for i in relevant)
    return "\n\n".join(lines)


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("wiki"))
async def wiki_group(message: Message) -> None:
    query = _extract_query(message)
    if not query:
        await message.reply(_EMPTY_QUERY_HINT)
        return

    telegram_id = message.from_user.id if message.from_user else None
    team_id = await get_team_id(message.chat.id, telegram_id)
    if not team_id:
        await message.reply(_NO_TEAM_MSG)
        return

    logger.info("wiki group query={!r} team={} user={}", query, team_id, telegram_id)
    results = await search_knowledge(query, team_id, limit=3)
    formatted = _format_results(results, query)
    if not formatted:
        await message.reply(_NO_RESULTS_TPL.format(q=escape(query)))
        return

    await message.reply(formatted)


@router.message(F.chat.type == "private", Command("wiki"))
async def wiki_private(message: Message) -> None:
    query = _extract_query(message)
    if not query:
        await message.answer(_EMPTY_QUERY_HINT)
        return

    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        await message.answer(_NO_TEAM_MSG)
        return

    teams = await get_member_teams(telegram_id)
    if not teams:
        await message.answer(_NO_TEAM_MSG)
        return

    team_id = str(teams[0].get("id", ""))
    if not team_id:
        await message.answer(_NO_TEAM_MSG)
        return

    logger.info("wiki private query={!r} team={} user={}", query, team_id, telegram_id)
    results = await search_knowledge(query, team_id, limit=3)
    formatted = _format_results(results, query)
    if not formatted:
        await message.answer(_NO_RESULTS_TPL.format(q=escape(query)))
        return

    await message.answer(formatted)
