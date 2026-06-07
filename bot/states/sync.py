from aiogram.fsm.state import State, StatesGroup


class SyncEditStates(StatesGroup):
    waiting_for_new_title = State()


class SyncRejectStates(StatesGroup):
    waiting_for_new_title = State()
