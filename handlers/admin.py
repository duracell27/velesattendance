import re
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from filters import IsAdmin
from services import sheets
from states import AdminStates
from utils import validate_full_name

router = Router()
router.message.filter(IsAdmin())


@router.message(Command("workers"))
async def cmd_workers(message: Message):
    workers = sheets.get_all_workers()
    if not workers:
        await message.answer("Немає зареєстрованих працівників.")
        return
    lines = []
    for w in workers:
        name = w["Ім'я Прізвище"]
        lines.append(f"{name} (ID: {w['Telegram ID']})")
    await message.answer("👥 Зареєстровані працівники:\n\n" + "\n".join(lines))


@router.message(Command("today"))
async def cmd_today(message: Message):
    records = sheets.get_today_attendance()
    if not records:
        await message.answer("Сьогодні ще ніхто не відмічався.")
        return
    at_work = [r for r in records if r.get("Прийшла") and not r.get("Пішла")]
    left = [r for r in records if r.get("Пішла")]
    lines = []
    if at_work:
        lines.append("✅ Зараз на роботі:")
        for r in at_work:
            name = r["Ім'я Прізвище"]
            lines.append(f"  • {name} (з {r['Прийшла']})")
    if left:
        lines.append("\n🚪 Вже пішли:")
        for r in left:
            name = r["Ім'я Прізвище"]
            lines.append(f"  • {name} ({r['Прийшла']} – {r['Пішла']}, {r['Відпрацьовано']})")
    await message.answer("\n".join(lines))


@router.message(Command("rename"))
async def cmd_rename(message: Message, state: FSMContext):
    workers = sheets.get_all_workers()
    if not workers:
        await message.answer("Немає зареєстрованих працівників.")
        return
    lines = []
    for w in workers:
        name = w["Ім'я Прізвище"]
        lines.append(f"{name} — ID: {w['Telegram ID']}")
    await message.answer(
        "Введіть Telegram ID працівника для перейменування:\n\n" + "\n".join(lines)
    )
    await state.set_state(AdminStates.rename_waiting_for_id)


@router.message(AdminStates.rename_waiting_for_id)
async def rename_get_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Невірний ID. Введіть числовий Telegram ID.")
        return
    worker = sheets.get_user(telegram_id)
    if not worker:
        await message.answer("Працівника з таким ID не знайдено.")
        return
    old_name = worker["Ім'я Прізвище"]
    await state.update_data(rename_id=telegram_id, old_name=old_name)
    await message.answer(
        f"Поточне ім'я: {old_name}\nВведіть нове ім'я та прізвище:"
    )
    await state.set_state(AdminStates.rename_waiting_for_name)


@router.message(AdminStates.rename_waiting_for_name)
async def rename_get_name(message: Message, state: FSMContext):
    new_name = message.text.strip() if message.text else ""
    if not validate_full_name(new_name):
        await message.answer("Будь ласка, введіть справжнє ім'я та прізвище.")
        return
    data = await state.get_data()
    sheets.rename_worker(data["rename_id"], new_name)
    await state.clear()
    await message.answer(f"✅ Перейменовано: {data['old_name']} → {new_name}")


@router.message(Command("delete_worker"))
async def cmd_delete(message: Message, state: FSMContext):
    workers = sheets.get_all_workers()
    if not workers:
        await message.answer("Немає зареєстрованих працівників.")
        return
    lines = []
    for w in workers:
        name = w["Ім'я Прізвище"]
        lines.append(f"{name} — ID: {w['Telegram ID']}")
    await message.answer(
        "Введіть Telegram ID працівника для видалення:\n\n" + "\n".join(lines)
    )
    await state.set_state(AdminStates.delete_waiting_for_id)


@router.message(AdminStates.delete_waiting_for_id)
async def delete_get_id(message: Message, state: FSMContext):
    try:
        telegram_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("Невірний ID.")
        return
    worker = sheets.get_user(telegram_id)
    if not worker:
        await message.answer("Працівника з таким ID не знайдено.")
        return
    name = worker["Ім'я Прізвище"]
    sheets.delete_worker(telegram_id)
    await state.clear()
    await message.answer(f"✅ Працівника {name} видалено.")


@router.message(Command("edit_record"))
async def cmd_edit(message: Message, state: FSMContext):
    await message.answer("Введіть ім'я та прізвище працівника (як в таблиці):")
    await state.set_state(AdminStates.edit_waiting_for_name)


@router.message(AdminStates.edit_waiting_for_name)
async def edit_get_name(message: Message, state: FSMContext):
    await state.update_data(edit_name=message.text.strip() if message.text else "")
    await message.answer("Введіть дату запису (наприклад: 22.05.2026):")
    await state.set_state(AdminStates.edit_waiting_for_date)


@router.message(AdminStates.edit_waiting_for_date)
async def edit_get_date(message: Message, state: FSMContext):
    date_str = message.text.strip() if message.text else ""
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
        await message.answer(
            "Невірний формат. Введіть дату у форматі ДД.ММ.РРРР (наприклад: 22.05.2026):"
        )
        return
    await state.update_data(edit_date=date_str)
    await message.answer("Що коригуємо?\nВведіть: Прийшла або Пішла")
    await state.set_state(AdminStates.edit_waiting_for_field)


@router.message(AdminStates.edit_waiting_for_field)
async def edit_get_field(message: Message, state: FSMContext):
    field = message.text.strip() if message.text else ""
    if field not in ("Прийшла", "Пішла"):
        await message.answer("Введіть: Прийшла або Пішла")
        return
    await state.update_data(edit_field=field)
    await message.answer("Введіть новий час (наприклад: 09:05):")
    await state.set_state(AdminStates.edit_waiting_for_time)


@router.message(AdminStates.edit_waiting_for_time)
async def edit_get_time(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not re.match(r"^\d{2}:\d{2}$", time_str):
        await message.answer(
            "Невірний формат. Введіть час у форматі ГГ:ХХ (наприклад: 09:05):"
        )
        return
    data = await state.get_data()
    success = sheets.edit_record(data["edit_name"], data["edit_date"], data["edit_field"], time_str)
    await state.clear()
    if success:
        await message.answer(
            f"✅ Запис оновлено: {data['edit_name']}, {data['edit_date']}, "
            f"{data['edit_field']} → {time_str}"
        )
    else:
        await message.answer("❌ Запис не знайдено. Перевірте ім'я та дату.")
