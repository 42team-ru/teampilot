from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Invite:
    token: str
    created_by: int
    used_by: Optional[int] = None


@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    full_name: str
    yougile_token: Optional[str] = None


# In-memory stores
_invites: dict[str, Invite] = {}
_users: dict[int, User] = {}


def create_invite(admin_id: int) -> str:
    token = "inv_" + secrets.token_hex(4)
    _invites[token] = Invite(token=token, created_by=admin_id)
    return token


def get_invite(token: str) -> Optional[Invite]:
    return _invites.get(token)


def use_invite(token: str, user_id: int) -> None:
    invite = _invites.get(token)
    if invite:
        invite.used_by = user_id


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
