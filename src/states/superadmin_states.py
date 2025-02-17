from aiogram.fsm.state import State, StatesGroup

class SuperadminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_admin_username = State()
    waiting_for_media_id = State()
    waiting_for_media_username = State()
    waiting_for_media_outlet = State() 