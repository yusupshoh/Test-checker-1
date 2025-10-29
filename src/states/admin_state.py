from aiogram.fsm.state import StatesGroup, State

class AdminFSM(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_deadmin_id = State()
    waiting_for_broadcast_message = State()
    waiting_for_next_broadcast_message = State()
    waiting_for_cleanup_confirmation = State()
    waiting_for_new_description = State()
    waiting_for_new_about = State()
    waiting_for_new_photo = State()