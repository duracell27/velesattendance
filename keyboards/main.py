from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard(
    checked_in: bool = False,
    checked_out: bool = False,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    if is_admin:
        buttons = [
            [KeyboardButton(text="📊 Звіт відвідуваності")],
            [KeyboardButton(text="📝 Редагувати графік")],
        ]
    elif checked_out:
        buttons = [
            [KeyboardButton(text="📊 Моя відвідуваність")],
        ]
    elif checked_in:
        buttons = [
            [KeyboardButton(text="🚪 Пішла з роботи")],
            [KeyboardButton(text="📊 Моя відвідуваність")],
        ]
    else:
        buttons = [
            [KeyboardButton(text="✅ Прийшла на роботу")],
            [KeyboardButton(text="🚪 Пішла з роботи")],
            [KeyboardButton(text="📊 Моя відвідуваність")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, persistent=True)
