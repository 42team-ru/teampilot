_sync_users: dict[int, list[str]] = {}


def add_sync_user(user_id: int) -> None:
    _sync_users[user_id] = []


def add_task_message(user_id: int, text: str) -> None:
    if user_id in _sync_users:
        _sync_users[user_id].append(text)


def get_task_messages(user_id: int) -> list[str]:
    return list(_sync_users.get(user_id, []))


def remove_sync_user(user_id: int) -> list[str]:
    return _sync_users.pop(user_id, [])


def is_in_sync(user_id: int) -> bool:
    return user_id in _sync_users


def clear_sync_users() -> None:
    _sync_users.clear()
