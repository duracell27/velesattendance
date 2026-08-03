from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def ar_month_keyboard(months: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=m, callback_data=f"ar:month:{m}")] for m in months]
    rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="ar:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ar_worker_keyboard(workers: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(workers), 2):
        row = [
            InlineKeyboardButton(
                text=workers[i + j]["Ім'я Прізвище"],
                callback_data=f"ar:worker:{i + j}",
            )
            for j in range(min(2, len(workers) - i))
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="ar:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
