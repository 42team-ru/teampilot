from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

_MAX_TITLE_LEN = 32
_MAX_TEAMS = 8


def build_teams_keyboard(teams: list[dict]) -> InlineKeyboardMarkup:
    """teams: [{"id": str, "chatTitle": str | None}, ...]. Max 8 items shown."""
    buttons = []
    for team in teams[:_MAX_TEAMS]:
        title = (team.get("chatTitle") or team["id"])[:_MAX_TITLE_LEN]
        buttons.append([InlineKeyboardButton(
            text=f"👥 {title}",
            callback_data=f"link_team:{team['id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
