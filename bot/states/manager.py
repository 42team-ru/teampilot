from aiogram.fsm.state import State, StatesGroup


class ManagerUpdateStates(StatesGroup):
    waiting_for_chat_title = State()


class ManagerLinkChatStates(StatesGroup):
    waiting_for_team_select = State()


class ManagerMeetingStates(StatesGroup):
    waiting_for_url = State()
