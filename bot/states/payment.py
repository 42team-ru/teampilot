from aiogram.fsm.state import State, StatesGroup


class TeamCreateStates(StatesGroup):
    waiting_name = State()
