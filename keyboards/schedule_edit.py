import calendar
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Додати", callback_data="se:action:add"),
            InlineKeyboardButton(text="✏️ Редагувати", callback_data="se:action:edit"),
            InlineKeyboardButton(text="🗑 Видалити", callback_data="se:action:delete"),
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel")],
    ])


def month_keyboard(months: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=m, callback_data=f"se:month:{m}")] for m in months]
    rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def worker_keyboard(workers: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(workers), 2):
        row = [
            InlineKeyboardButton(
                text=workers[i + j]["Ім'я Прізвище"],
                callback_data=f"se:worker:{i + j}",
            )
            for j in range(min(2, len(workers) - i))
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def day_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    days_in_month = calendar.monthrange(year, month)[1]
    buttons = [
        InlineKeyboardButton(text=str(d), callback_data=f"se:day:{d}")
        for d in range(1, days_in_month + 1)
    ]
    rows = [buttons[i:i + 5] for i in range(0, len(buttons), 5)]
    rows.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def field_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🕐 Прийшла", callback_data="se:field:Прийшла"),
            InlineKeyboardButton(text="🕐 Пішла", callback_data="se:field:Пішла"),
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel")],
    ])


def confirm_delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, видалити", callback_data="se:confirm:yes"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data="se:cancel"),
        ],
    ])
