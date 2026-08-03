from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from config import ALL_ADMIN_IDS
from filters import IsAdmin
from services import sheets
from states import AdminReportStates
from keyboards.admin_report import ar_month_keyboard, ar_worker_keyboard
from utils import format_date, now_kyiv

router = Router()
router.message.filter(IsAdmin())


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


@router.message(F.text == "📊 Звіт відвідуваності", StateFilter(default_state))
async def admin_report_start(message: Message, state: FSMContext):
    months = sheets.get_available_months()
    if not months:
        await message.answer("❌ Немає доступних місяців в таблиці.")
        return
    await message.answer("Виберіть місяць:", reply_markup=ar_month_keyboard(months))
    await state.set_state(AdminReportStates.choosing_month)


@router.callback_query(F.data == "ar:cancel", StateFilter(AdminReportStates))
async def ar_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано.")
    await callback.answer()


@router.callback_query(F.data.startswith("ar:month:"), StateFilter(AdminReportStates.choosing_month))
async def ar_month_selected(callback: CallbackQuery, state: FSMContext):
    sheet_name = callback.data.split(":", 2)[2]
    await state.update_data(sheet_name=sheet_name)
    workers = _get_non_admin_workers()
    if not workers:
        await callback.message.edit_text("❌ Немає зареєстрованих працівників.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text(
        "Виберіть працівника:", reply_markup=ar_worker_keyboard(workers)
    )
    await state.set_state(AdminReportStates.choosing_worker)
    await callback.answer()


@router.callback_query(F.data.startswith("ar:worker:"), StateFilter(AdminReportStates.choosing_worker))
async def ar_worker_selected(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":", 2)[2])
    workers = _get_non_admin_workers()
    worker_name = workers[idx]["Ім'я Прізвище"]
    data = await state.get_data()
    sheet_name = data["sheet_name"]
    await state.clear()

    records = sheets.get_attendance_by_name_and_month(worker_name, sheet_name)
    if not records:
        await callback.message.edit_text("📊 Немає записів за цей місяць.")
        await callback.answer()
        return

    today_str = format_date(now_kyiv())
    total_minutes = 0
    lines = []

    for r in records:
        date = r.get("Дата", "")
        checkin = r.get("Прийшла", "")
        checkout = r.get("Пішла", "")
        hours_str = r.get("Відпрацьовано", "")

        if checkout and hours_str:
            line = f"📅 {date} | {checkin} - {checkout} | {hours_str}"
            try:
                parts = hours_str.split()
                total_minutes += int(parts[0]) * 60 + int(parts[2])
            except (IndexError, ValueError):
                pass
        elif date == today_str and not checkout:
            line = f"📅 {date} | {checkin} - ... | ⏳ в процесі"
        else:
            line = f"📅 {date} | {checkin} - — | не завершено"

        lines.append(line)

    total_h = total_minutes // 60
    total_m = total_minutes % 60
    text = (
        f"📊 <b>Відвідуваність {worker_name} — {sheet_name}:</b>\n\n"
        + "\n".join(lines)
        + f"\n\n<b>Загалом за місяць: {total_h} год {total_m} хв</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()
