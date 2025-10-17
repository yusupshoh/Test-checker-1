from aiogram.fsm.state import State, StatesGroup

class RS(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone_number = State()

class PS(StatesGroup):
    editing_first_name = State()
    editing_last_name = State()
    editing_phone_number = State()