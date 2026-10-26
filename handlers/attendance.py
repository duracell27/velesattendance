import logging
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove
from services import sheets, notifications
from states import AttendanceStates
from keyboards.main import get_main_keyboard
from utils import format_time, format_date, now_kyiv, calculate_hours_worked
from config import ALL_ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "✅ Прийшла на роботу", StateFilter(default_state))
async def checkin_button(message: Message, state: FSMContext):
    try:
        user = sheets.get_user(message.from_user.id)
        if not user:
            await message.answer("Спочатку зареєструйтесь. Надішліть /start")
            return
        record = sheets.get_today_checkin(message.from_user.id)
        if record:
            if record.get("Пішла"):
                await message.answer(
                    "❌ Ви вже завершили робочий день сьогодні. Повторна реєстрація приходу неможлива.",
                    reply_markup=get_main_keyboard(checked_out=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
                )
            else:
                await message.answer(
                    f"❌ Ви вже зареєстровані на роботі сьогодні о {record.get('Прийшла')}.",
                    reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
                )
            return
        await message.answer("📸 Надішліть фото для підтвердження приходу:")
        await state.set_state(AttendanceStates.waiting_for_checkin_photo)
    except Exception:
        logger.exception("Error in checkin_button for user %s", message.from_user.id)
        await message.answer(
            "❌ Виникла помилка. Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
        )


@router.message(AttendanceStates.waiting_for_checkin_photo, F.photo)
async def process_checkin_photo(message: Message, state: FSMContext, bot: Bot):
    try:
        user = sheets.get_user(message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Помилка: ваш профіль не знайдено. Надішліть /start")
            return
        name = user["Ім'я Прізвище"]
        time_str = format_time(now_kyiv())
        photo_file_id = message.photo[-1].file_id

        existing = sheets.get_today_checkin(message.from_user.id)
        if existing:
            await state.clear()
            await message.answer(
                f"❌ Ви вже зареєстровані на роботі сьогодні о {existing.get('Прийшла')}.",
                reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
            )
            return

        sheets.append_checkin(name, time_str)
        await state.clear()
        await message.answer(
            f"✅ Ви успішно зареєстровані на роботі о {time_str}",
            reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
        )
        try:
            await notifications.notify_hr_checkin(bot, name, time_str, photo_file_id)
        except Exception:
            logger.exception("Failed to send checkin notification for %s", name)
    except Exception:
        logger.exception("Error in process_checkin_photo for user %s", message.from_user.id)
        await state.clear()
        await message.answer(
            "❌ Виникла помилка при реєстрації приходу. Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
        )


@router.message(AttendanceStates.waiting_for_checkin_photo)
async def checkin_not_photo(message: Message):
    await message.answer("Будь ласка, надішліть фото (не файл і не текст).")


@router.message(F.text == "🚪 Пішла з роботи", StateFilter(default_state))
async def checkout_button(message: Message, state: FSMContext):
    try:
        user = sheets.get_user(message.from_user.id)
        if not user:
            await message.answer("Спочатку зареєструйтесь. Надішліть /start")
            return
        record = sheets.get_today_checkin(message.from_user.id)
        if not record:
            await message.answer(
                "❌ Ви ще не зареєструвались на роботі сьогодні. Спочатку натисніть «Прийшла на роботу».",
                reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
            )
            return
        if record.get("Пішла"):
            await message.answer(
                f"❌ Ви вже відмітили вихід з роботи сьогодні о {record.get('Пішла')}.",
                reply_markup=get_main_keyboard(checked_out=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
            )
            return
        await message.answer("📸 Надішліть фото для підтвердження виходу:")
        await state.set_state(AttendanceStates.waiting_for_checkout_photo)
    except Exception:
        logger.exception("Error in checkout_button for user %s", message.from_user.id)
        await message.answer(
            "❌ Виникла помилка. Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
        )


@router.message(AttendanceStates.waiting_for_checkout_photo, F.photo)
async def process_checkout_photo(message: Message, state: FSMContext, bot: Bot):
    try:
        user = sheets.get_user(message.from_user.id)
        if not user:
            await state.clear()
            await message.answer("Помилка: ваш профіль не знайдено. Надішліть /start")
            return
        name = user["Ім'я Прізвище"]
        now = now_kyiv()
        time_str = format_time(now)

        checkin_record = sheets.get_today_checkin(message.from_user.id)
        if not checkin_record:
            await state.clear()
            await message.answer(
                "❌ Запис про прихід не знайдено. Зверніться до адміністратора.",
                reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
            )
            return
        if checkin_record.get("Пішла"):
            await state.clear()
            await message.answer(
                f"❌ Ви вже відмітили вихід сьогодні о {checkin_record.get('Пішла')}.",
                reply_markup=get_main_keyboard(checked_out=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
            )
            return

        hours_str = calculate_hours_worked(checkin_record["Прийшла"], time_str)
        photo_file_id = message.photo[-1].file_id

        sheets.update_checkout(name, time_str, hours_str)
        sheets.update_monthly_summary(now)
        await state.clear()
        await message.answer(
            f"✅ До побачення! Ви пішли з роботи о {time_str}. Відпрацьовано: {hours_str}",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            await notifications.notify_hr_checkout(bot, name, time_str, hours_str, photo_file_id)
        except Exception:
            logger.exception("Failed to send checkout notification for %s", name)
    except Exception:
        logger.exception("Error in process_checkout_photo for user %s", message.from_user.id)
        await state.clear()
        await message.answer(
            "❌ Виникла помилка при реєстрації виходу. Спробуйте ще раз або зверніться до адміністратора.",
            reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS),
        )


@router.message(AttendanceStates.waiting_for_checkout_photo)
async def checkout_not_photo(message: Message):
    await message.answer("Будь ласка, надішліть фото (не файл і не текст).")


@router.message(F.photo, StateFilter(default_state))
async def photo_in_default_state(message: Message):
    await message.answer(
        "📸 Фото отримано, але зараз не очікується.\n"
        "Спочатку натисніть кнопку «✅ Прийшла на роботу» або «🚪 Пішла з роботи», "
        "а потім надішліть фото.",
        reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS),
    )


@router.message(F.text == "📊 Моя відвідуваність", StateFilter(default_state))
async def my_attendance(message: Message):
    user = sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Спочатку зареєструйтесь. Надішліть /start")
        return

    records = sheets.get_user_monthly_attendance(message.from_user.id)
    if not records:
        await message.answer("📊 Немає записів відвідуваності за поточний місяць.")
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

    text = "📊 <b>Моя відвідуваність за поточний місяць:</b>\n\n"
    text += "\n".join(lines)
    text += f"\n\n<b>Загалом за місяць: {total_h} год {total_m} хв</b>"

    checked_in = sheets.get_today_checkin(message.from_user.id)
    is_checked_in = bool(checked_in and not checked_in.get("Пішла"))

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(checked_in=is_checked_in, is_admin=message.from_user.id in ALL_ADMIN_IDS))
