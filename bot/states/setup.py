from aiogram.fsm.state import State, StatesGroup


class GroupSetupStates(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_company_select = State()
    waiting_for_board_select = State()


class LinkTeamStates(StatesGroup):
    waiting_for_team_select = State()


class CreateTeamStates(StatesGroup):
    waiting_for_admin_telegram_id = State()
    waiting_for_chat_title = State()
