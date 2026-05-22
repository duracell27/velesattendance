from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Прийшла на роботу")],
            [KeyboardButton(text="🚪 Пішла з роботи")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
