from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_name = State()


class AttendanceStates(StatesGroup):
    waiting_for_checkin_photo = State()
    waiting_for_checkout_photo = State()


class AdminStates(StatesGroup):
    rename_waiting_for_id = State()
    rename_waiting_for_name = State()
    delete_waiting_for_id = State()
    edit_waiting_for_name = State()
    edit_waiting_for_date = State()
    edit_waiting_for_field = State()
    edit_waiting_for_time = State()
