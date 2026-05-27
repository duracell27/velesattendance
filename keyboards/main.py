from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard(checked_in: bool = False) -> ReplyKeyboardMarkup:
    if checked_in:
        buttons = [[KeyboardButton(text="🚪 Пішла з роботи")]]
    else:
        buttons = [
            [KeyboardButton(text="✅ Прийшла на роботу")],
            [KeyboardButton(text="🚪 Пішла з роботи")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, persistent=True)
