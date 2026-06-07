from aiogram.fsm.state import State, StatesGroup


class CoursesAddStates(StatesGroup):
    waiting_for_url = State()
