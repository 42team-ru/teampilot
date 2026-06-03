from aiogram.fsm.state import State, StatesGroup


class GroupSetupStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_board_select = State()


class LinkTeamStates(StatesGroup):
    waiting_for_team_select = State()


class CreateTeamStates(StatesGroup):
    waiting_for_chat_title = State()
    waiting_for_kanban_id = State()
    waiting_for_kanban_api_key = State()
