from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()


class JoinTeamStates(StatesGroup):
    waiting_for_yougile_login = State()
    waiting_for_yougile_password = State()


class UpdateYouGileStates(StatesGroup):
    waiting_for_yougile_login = State()
    waiting_for_yougile_password = State()
