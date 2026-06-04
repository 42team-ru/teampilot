from aiogram.fsm.state import State, StatesGroup


class ManagerUpdateStates(StatesGroup):
    waiting_for_chat_title = State()
    waiting_for_kanban_id = State()
    waiting_for_kanban_api_key = State()


class ManagerLinkChatStates(StatesGroup):
    waiting_for_team_select = State()
