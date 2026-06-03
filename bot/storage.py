from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    full_name: str
    yougile_token: Optional[str] = None


# In-memory stores
_users: dict[int, User] = {}


def register_user(telegram_id: int, username: Optional[str], full_name: str) -> User:
    user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    _users[telegram_id] = user
    return user


def get_user(telegram_id: int) -> Optional[User]:
    return _users.get(telegram_id)


def save_yougile_token(telegram_id: int, token: str) -> None:
    user = _users.get(telegram_id)
    if user:
        user.yougile_token = token


# ── Group storage ────────────────────────────────────────────────────────────

@dataclass
class Group:
    chat_id: int
    chat_title: str
    added_by_telegram_id: int
    yougile_token: str
    yougile_board_id: str
    active: bool = True


_groups: dict[int, Group] = {}


def save_group(
    chat_id: int,
    chat_title: str,
    added_by_telegram_id: int,
    yougile_token: str,
    yougile_board_id: str,
) -> Group:
    group = Group(
        chat_id=chat_id,
        chat_title=chat_title,
        added_by_telegram_id=added_by_telegram_id,
        yougile_token=yougile_token,
        yougile_board_id=yougile_board_id,
        active=True,
    )
    _groups[chat_id] = group
    return group


def get_group_local(chat_id: int) -> Optional[Group]:
    return _groups.get(chat_id)


def deactivate_group_local(chat_id: int) -> None:
    group = _groups.get(chat_id)
    if group:
        group.active = False


@dataclass
class PendingChat:
    chat_id: int
    chat_title: str
    added_by_telegram_id: int
    active: bool = True


_pending_chats: dict[int, PendingChat] = {}


def save_pending_chat(chat_id: int, chat_title: str, added_by_telegram_id: int) -> PendingChat:
    pending_chat = PendingChat(
        chat_id=chat_id,
        chat_title=chat_title,
        added_by_telegram_id=added_by_telegram_id,
        active=True,
    )
    _pending_chats[chat_id] = pending_chat
    return pending_chat


def list_pending_chats(added_by_telegram_id: int) -> list[PendingChat]:
    return [
        chat
        for chat in _pending_chats.values()
        if chat.added_by_telegram_id == added_by_telegram_id and chat.active
    ]


def get_pending_chat(chat_id: int, added_by_telegram_id: int) -> Optional[PendingChat]:
    chat = _pending_chats.get(chat_id)
    if chat is None or chat.added_by_telegram_id != added_by_telegram_id or not chat.active:
        return None
    return chat


def remove_pending_chat(chat_id: int) -> None:
    _pending_chats.pop(chat_id, None)


def deactivate_pending_chat(chat_id: int) -> None:
    chat = _pending_chats.get(chat_id)
    if chat:
        chat.active = False
