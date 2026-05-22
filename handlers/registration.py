from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from services import sheets
from states import RegistrationStates
from keyboards.main import get_main_keyboard
from utils import validate_full_name

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = sheets.get_user(message.from_user.id)
    if user:
        name = user["Ім'я Прізвище"]
        await message.answer(
            f"Привіт, {name}! Оберіть дію:",
            reply_markup=get_main_keyboard(),
        )
        return
    await message.answer(
        "Привіт! Для реєстрації введіть ваше ім'я та прізвище.\n"
        "Наприклад: Владимирська Тетяна"
    )
    await state.set_state(RegistrationStates.waiting_for_name)


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not validate_full_name(name):
        await message.answer(
            "Будь ласка, введіть справжнє ім'я та прізвище.\n"
            "Наприклад: Владимирська Тетяна"
        )
        return
    sheets.register_user(message.from_user.id, name)
    await state.clear()
    await message.answer(
        f"✅ Реєстрація успішна! Вітаємо, {name}!",
        reply_markup=get_main_keyboard(),
    )
