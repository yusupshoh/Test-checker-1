from aiogram.fsm.state import State, StatesGroup

class TestStates(StatesGroup):
    waiting_for_name = State()       # Test nomini kutish
    waiting_for_answer_key = State()

class CheckStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_user_answers = State()
    waiting_for_finish_code = State()
    waiting_for_template_selection = State()
    waiting_for_pagination = State()
