from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove
from services import sheets, notifications
from states import AttendanceStates
from keyboards.main import get_main_keyboard
from utils import format_time, now_kyiv, calculate_hours_worked

router = Router()


@router.message(F.text == "✅ Прийшла на роботу", StateFilter(default_state))
async def checkin_button(message: Message, state: FSMContext):
    user = sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Спочатку зареєструйтесь. Надішліть /start")
        return
    record = sheets.get_today_checkin(message.from_user.id)
    if record:
        if record.get("Пішла"):
            await message.answer(
                "❌ Ви вже завершили робочий день сьогодні. Повторна реєстрація приходу неможлива.",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await message.answer(
                f"❌ Ви вже зареєстровані на роботі сьогодні о {record.get('Прийшла')}.",
                reply_markup=get_main_keyboard(checked_in=True),
            )
        return
    await message.answer("📸 Надішліть фото для підтвердження приходу:")
    await state.set_state(AttendanceStates.waiting_for_checkin_photo)


@router.message(AttendanceStates.waiting_for_checkin_photo, F.photo)
async def process_checkin_photo(message: Message, state: FSMContext, bot: Bot):
    user = sheets.get_user(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Помилка: ваш профіль не знайдено. Надішліть /start")
        return
    name = user["Ім'я Прізвище"]
    time_str = format_time(now_kyiv())
    photo_file_id = message.photo[-1].file_id

    sheets.append_checkin(name, time_str)
    await state.clear()
    await message.answer(
        f"✅ Ви успішно зареєстровані на роботі о {time_str}",
        reply_markup=get_main_keyboard(checked_in=True),
    )
    await notifications.notify_hr_checkin(bot, name, time_str, photo_file_id)


@router.message(AttendanceStates.waiting_for_checkin_photo)
async def checkin_not_photo(message: Message):
    await message.answer("Будь ласка, надішліть фото (не файл і не текст).")


@router.message(F.text == "🚪 Пішла з роботи", StateFilter(default_state))
async def checkout_button(message: Message, state: FSMContext):
    user = sheets.get_user(message.from_user.id)
    if not user:
        await message.answer("Спочатку зареєструйтесь. Надішліть /start")
        return
    record = sheets.get_today_checkin(message.from_user.id)
    if not record:
        await message.answer(
            "❌ Ви ще не зареєструвались на роботі сьогодні. Спочатку натисніть «Прийшла на роботу».",
            reply_markup=get_main_keyboard(),
        )
        return
    if record.get("Пішла"):
        await message.answer(
            f"❌ Ви вже відмітили вихід з роботи сьогодні о {record.get('Пішла')}.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    await message.answer("📸 Надішліть фото для підтвердження виходу:")
    await state.set_state(AttendanceStates.waiting_for_checkout_photo)


@router.message(AttendanceStates.waiting_for_checkout_photo, F.photo)
async def process_checkout_photo(message: Message, state: FSMContext, bot: Bot):
    user = sheets.get_user(message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Помилка: ваш профіль не знайдено. Надішліть /start")
        return
    name = user["Ім'я Прізвище"]
    now = now_kyiv()
    time_str = format_time(now)

    checkin_record = sheets.get_today_checkin(message.from_user.id)
    hours_str = calculate_hours_worked(checkin_record["Прийшла"], time_str)
    photo_file_id = message.photo[-1].file_id

    sheets.update_checkout(name, time_str, hours_str)
    sheets.update_monthly_summary(now)
    await state.clear()
    await message.answer(
        f"✅ До побачення! Ви пішли з роботи о {time_str}. Відпрацьовано: {hours_str}",
        reply_markup=ReplyKeyboardRemove(),
    )
    await notifications.notify_hr_checkout(bot, name, time_str, hours_str, photo_file_id)


@router.message(AttendanceStates.waiting_for_checkout_photo)
async def checkout_not_photo(message: Message):
    await message.answer("Будь ласка, надішліть фото (не файл і не текст).")
