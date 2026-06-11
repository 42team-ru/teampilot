_sync_users: dict[int, list[str]] = {}


def add_sync_user(user_id: int) -> None:
    _sync_users[user_id] = []


def remove_sync_user(user_id: int) -> list[str]:
    return _sync_users.pop(user_id, [])


def is_in_sync(user_id: int) -> bool:
    return user_id in _sync_users


def clear_sync_users() -> None:
    _sync_users.clear()
