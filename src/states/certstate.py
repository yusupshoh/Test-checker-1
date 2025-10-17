from aiogram.fsm.state import State, StatesGroup

class CertStates(StatesGroup):
    selecting_template = State()