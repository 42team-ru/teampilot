from aiogram.fsm.state import State, StatesGroup


class GroupSetupStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_board_select = State()
