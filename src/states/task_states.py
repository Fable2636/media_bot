from aiogram.fsm.state import State, StatesGroup

class TaskStates(StatesGroup):
    waiting_for_press_release = State()
    waiting_for_photo = State()
    waiting_for_deadline = State()
    waiting_for_submission = State()
    waiting_for_revision = State()
    waiting_for_link = State()
    waiting_for_text = State()

class AdminStates(StatesGroup):
    waiting_for_task_photo = State()