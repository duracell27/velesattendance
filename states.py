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


class ScheduleEditStates(StatesGroup):
    choosing_action = State()
    choosing_month = State()
    choosing_worker = State()
    choosing_day = State()
    entering_arrival = State()
    entering_departure = State()
    choosing_field = State()
    entering_new_time = State()
    confirming_delete = State()


class AdminReportStates(StatesGroup):
    choosing_month = State()
    choosing_worker = State()
