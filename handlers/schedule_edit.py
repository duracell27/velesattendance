import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from config import ALL_ADMIN_IDS
from services import sheets
from states import ScheduleEditStates
from filters import IsAdmin
from keyboards.schedule_edit import (
    action_keyboard, month_keyboard, worker_keyboard,
    day_keyboard, field_keyboard, confirm_delete_keyboard,
)
from utils import MONTH_NAMES_UK, calculate_hours_worked

router = Router()
router.message.filter(IsAdmin())

_MONTH_NUM = {name: num for num, name in MONTH_NAMES_UK.items()}


def _get_non_admin_workers() -> list[dict]:
    seen_names: set[str] = set()
    result = []
    for w in sheets.get_all_workers():
        tid = int(w.get("Telegram ID", 0))
        name = w.get("Ім'я Прізвище", "")
        if tid not in ALL_ADMIN_IDS and name and name not in seen_names:
            seen_names.add(name)
            result.append(w)
    return result

TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _parse_sheet_name(sheet_name: str) -> tuple[int, int]:
    """Return (year, month_number) from 'Серпень 2026'."""
    name, year = sheet_name.split(" ")
    return int(year), _MONTH_NUM[name]


def _build_date_str(sheet_name: str, day: int) -> str:
    year, month = _parse_sheet_name(sheet_name)
    return f"{day:02d}.{month:02d}.{year}"


# ── Entry point ──────────────────────────────────────────────────────────────

@router.message(F.text == "📝 Редагувати графік", StateFilter(default_state))
async def schedule_edit_start(message: Message, state: FSMContext):
    await message.answer("Оберіть дію:", reply_markup=action_keyboard())
    await state.set_state(ScheduleEditStates.choosing_action)


# ── Cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), StateFilter(ScheduleEditStates))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")


@router.callback_query(F.data == "se:cancel", StateFilter(ScheduleEditStates))
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано.")
    await callback.answer()


# ── Step 1: Action ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:action:"), StateFilter(ScheduleEditStates.choosing_action))
async def action_selected(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 2)[2]
    await state.update_data(action=action)
    months = sheets.get_available_months()
    if not months:
        await callback.message.edit_text("❌ Немає доступних місяців в таблиці.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text("Виберіть місяць:", reply_markup=month_keyboard(months))
    await state.set_state(ScheduleEditStates.choosing_month)
    await callback.answer()


# ── Step 2: Month ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:month:"), StateFilter(ScheduleEditStates.choosing_month))
async def month_selected(callback: CallbackQuery, state: FSMContext):
    sheet_name = callback.data.split(":", 2)[2]
    await state.update_data(sheet_name=sheet_name)
    workers = _get_non_admin_workers()
    if not workers:
        await callback.message.edit_text("❌ Немає зареєстрованих працівників.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text("Виберіть працівника:", reply_markup=worker_keyboard(workers))
    await state.set_state(ScheduleEditStates.choosing_worker)
    await callback.answer()


# ── Step 3: Worker ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:worker:"), StateFilter(ScheduleEditStates.choosing_worker))
async def worker_selected(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":", 2)[2])
    workers = _get_non_admin_workers()
    worker_name = workers[idx]["Ім'я Прізвище"]
    await state.update_data(worker_name=worker_name)
    data = await state.get_data()
    year, month = _parse_sheet_name(data["sheet_name"])
    await callback.message.edit_text(
        "Виберіть число:", reply_markup=day_keyboard(year, month)
    )
    await state.set_state(ScheduleEditStates.choosing_day)
    await callback.answer()


# ── Step 4: Day → branch by action ───────────────────────────────────────────

@router.callback_query(F.data.startswith("se:day:"), StateFilter(ScheduleEditStates.choosing_day))
async def day_selected(callback: CallbackQuery, state: FSMContext):
    day = int(callback.data.split(":", 2)[2])
    await state.update_data(day=day)
    data = await state.get_data()
    action = data["action"]
    date_str = _build_date_str(data["sheet_name"], day)

    if action == "add":
        await callback.message.edit_text(
            f"➕ Додавання: {data['worker_name']}, {date_str}\n\n"
            "Введіть час приходу (ГГ:ХХ):"
        )
        await state.set_state(ScheduleEditStates.entering_arrival)

    elif action == "edit":
        await callback.message.edit_text(
            f"✏️ Редагування: {data['worker_name']}, {date_str}\n\nЩо редагуємо?",
            reply_markup=field_keyboard(),
        )
        await state.set_state(ScheduleEditStates.choosing_field)

    elif action == "delete":
        date_str = _build_date_str(data["sheet_name"], day)
        record = sheets.get_record(date_str, data["worker_name"])
        if not record:
            await callback.message.edit_text("❌ Запис не знайдено.")
            await state.clear()
            await callback.answer()
            return
        info = (
            f"📅 {date_str}  👤 {data['worker_name']}\n"
            f"🕐 Прийшла: {record.get('Прийшла', '—')}\n"
            f"🕐 Пішла: {record.get('Пішла', '—')}\n"
            f"⏱ Відпрацьовано: {record.get('Відпрацьовано', '—')}"
        )
        await callback.message.edit_text(
            f"🗑 Видалення запису:\n\n{info}\n\nПідтвердити?",
            reply_markup=confirm_delete_keyboard(),
        )
        await state.set_state(ScheduleEditStates.confirming_delete)

    await callback.answer()


# ── Add: arrival ─────────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_arrival))
async def enter_arrival(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 09:05):")
        return
    await state.update_data(arrival=time_str)
    await message.answer("Введіть час виходу (ГГ:ХХ):")
    await state.set_state(ScheduleEditStates.entering_departure)


# ── Add: departure ───────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_departure))
async def enter_departure(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 17:00):")
        return
    data = await state.get_data()
    arr_h, arr_m = map(int, data["arrival"].split(":"))
    dep_h, dep_m = map(int, time_str.split(":"))
    if dep_h * 60 + dep_m <= arr_h * 60 + arr_m:
        await message.answer(
            "❌ Час виходу не може бути раніше або рівним часу приходу. Введіть знову:"
        )
        return
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.add_record(date_str, data["worker_name"], data["arrival"], time_str)
    await state.clear()
    if success:
        hours = calculate_hours_worked(data["arrival"], time_str)
        await message.answer(
            f"✅ Запис додано:\n{data['worker_name']}, {date_str}\n"
            f"Прийшла: {data['arrival']}, Пішла: {time_str}, Відпрацьовано: {hours}"
        )
    else:
        await message.answer("❌ Запис за цю дату вже існує.")


# ── Edit: field selection ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:field:"), StateFilter(ScheduleEditStates.choosing_field))
async def field_selected(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 2)[2]
    await state.update_data(field=field)
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    await callback.message.edit_text(
        f"✏️ {data['worker_name']}, {date_str} — {field}\n\nВведіть новий час (ГГ:ХХ):"
    )
    await state.set_state(ScheduleEditStates.entering_new_time)
    await callback.answer()


# ── Edit: new time ────────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_new_time))
async def enter_new_time(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 09:05):")
        return
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.edit_record(data["worker_name"], date_str, data["field"], time_str)
    await state.clear()
    if success:
        await message.answer(
            f"✅ Оновлено: {data['worker_name']}, {date_str}\n"
            f"{data['field']} → {time_str}"
        )
    else:
        await message.answer("❌ Запис не знайдено.")


# ── Delete: confirmed ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "se:confirm:yes", StateFilter(ScheduleEditStates.confirming_delete))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.delete_record(date_str, data["worker_name"])
    await state.clear()
    if success:
        await callback.message.edit_text(
            f"✅ Видалено: {data['worker_name']}, {date_str}"
        )
    else:
        await callback.message.edit_text("❌ Запис не знайдено.")
    await callback.answer()
