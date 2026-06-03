from aiogram.fsm.state import State, StatesGroup


class FileUploadStates(StatesGroup):
    waiting_for_file = State()
