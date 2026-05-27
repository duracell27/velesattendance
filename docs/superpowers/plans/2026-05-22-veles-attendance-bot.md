# Veles Attendance Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that records employee check-in/check-out with photos into Google Sheets, notifies HR, and provides admin management commands.

**Architecture:** aiogram 3.x with polling, MemoryStorage for FSM state, gspread for all data persistence via Google Sheets (no separate database). Handlers are split by responsibility into three routers (registration, attendance, admin) assembled in bot.py.

**Tech Stack:** Python 3.11+, aiogram 3.x, gspread 6.x, google-auth, python-dotenv, pytz, pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `bot.py` | Entry point — wires routers, starts polling |
| `config.py` | Loads env vars: token, admin IDs, spreadsheet ID |
| `utils.py` | Pure functions: time formatting, month name, hours calc, name validation |
| `states.py` | All FSM state groups |
| `filters.py` | `IsAdmin` filter |
| `keyboards/main.py` | Main reply keyboard (2 buttons) |
| `services/sheets.py` | All Google Sheets read/write operations + `_calculate_summary_from_values` |
| `services/notifications.py` | Forward photos to HR admin |
| `handlers/registration.py` | `/start`, name input FSM |
| `handlers/attendance.py` | Check-in / check-out button flows + photo FSM |
| `handlers/admin.py` | `/workers`, `/today`, `/rename`, `/delete_worker`, `/edit_record` + FSM |
| `tests/test_utils.py` | Unit tests for utils.py |
| `tests/test_sheets_logic.py` | Unit tests for `_calculate_summary_from_values` |
| `veles-bot.service` | systemd unit for VPS auto-start |

---

## Task 1: Project setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `handlers/__init__.py`, `services/__init__.py`, `keyboards/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/Apple/IT/velesattendance
mkdir -p handlers services keyboards tests
```

- [ ] **Step 2: Create requirements.txt**

```
aiogram==3.13.0
gspread==6.1.2
google-auth==2.29.0
python-dotenv==1.0.1
pytz==2024.1
pytest==8.1.1
```

- [ ] **Step 3: Create .env.example**

```
BOT_TOKEN=your_telegram_bot_token_here
HR_ADMIN_ID=123456789
REGULAR_ADMIN_IDS=987654321,111222333
SPREADSHEET_ID=your_google_spreadsheet_id_here
GOOGLE_CREDENTIALS_PATH=credentials.json
```

- [ ] **Step 4: Create empty __init__.py files**

Create empty files at:
- `handlers/__init__.py`
- `services/__init__.py`
- `keyboards/__init__.py`
- `tests/__init__.py`

- [ ] **Step 5: Create virtual environment and install dependencies**

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example handlers/__init__.py services/__init__.py keyboards/__init__.py tests/__init__.py
git commit -m "feat: initial project setup"
```

---

## Task 2: config.py

**Files:**
- Create: `config.py`
- Create: `.env` (from .env.example, filled with real values)

- [ ] **Step 1: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
HR_ADMIN_ID: int = int(os.getenv("HR_ADMIN_ID"))
REGULAR_ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("REGULAR_ADMIN_IDS", "").split(",")
    if x.strip()
]
ALL_ADMIN_IDS: list[int] = [HR_ADMIN_ID] + REGULAR_ADMIN_IDS
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
```

- [ ] **Step 2: Copy .env.example to .env and fill in real values**

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `BOT_TOKEN` — from @BotFather
- `HR_ADMIN_ID` — Telegram ID of the HR admin
- `REGULAR_ADMIN_IDS` — comma-separated Telegram IDs of other admins (can be empty)
- `SPREADSHEET_ID` — the part of the spreadsheet URL between `/d/` and `/edit`
- `GOOGLE_CREDENTIALS_PATH` — `credentials.json` (place the file in the project root)

- [ ] **Step 3: Verify config loads**

```bash
python -c "import config; print(config.BOT_TOKEN[:10], config.HR_ADMIN_ID)"
```

Expected: prints first 10 chars of token and HR admin ID number.

- [ ] **Step 4: Add .env and credentials.json to .gitignore**

Create `.gitignore`:
```
.env
credentials.json
venv/
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 5: Commit**

```bash
git add config.py .gitignore
git commit -m "feat: add config loader"
```

---

## Task 3: utils.py (TDD)

**Files:**
- Create: `utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests first**

Create `tests/test_utils.py`:

```python
from datetime import datetime
import pytest
from utils import (
    calculate_hours_worked,
    get_month_sheet_name,
    validate_full_name,
    format_date,
    format_time,
)


def test_calculate_hours_worked_exact_hours():
    assert calculate_hours_worked("09:00", "18:00") == "9 год 0 хв"


def test_calculate_hours_worked_with_minutes():
    assert calculate_hours_worked("09:05", "18:10") == "9 год 5 хв"


def test_calculate_hours_worked_short_shift():
    assert calculate_hours_worked("14:30", "17:45") == "3 год 15 хв"


def test_get_month_sheet_name_may():
    assert get_month_sheet_name(datetime(2026, 5, 22)) == "Травень 2026"


def test_get_month_sheet_name_december():
    assert get_month_sheet_name(datetime(2026, 12, 1)) == "Грудень 2026"


def test_get_month_sheet_name_january():
    assert get_month_sheet_name(datetime(2027, 1, 1)) == "Січень 2027"


def test_validate_full_name_valid():
    assert validate_full_name("Владимирська Тетяна") is True


def test_validate_full_name_three_words():
    assert validate_full_name("Іваненко Олена Петрівна") is True


def test_validate_full_name_single_word():
    assert validate_full_name("Тетяна") is False


def test_validate_full_name_empty():
    assert validate_full_name("") is False


def test_validate_full_name_short_parts():
    assert validate_full_name("А Б") is False


def test_format_date():
    assert format_date(datetime(2026, 5, 1)) == "01.05.2026"


def test_format_date_double_digit():
    assert format_date(datetime(2026, 11, 15)) == "15.11.2026"


def test_format_time():
    assert format_time(datetime(2026, 5, 1, 9, 5)) == "09:05"


def test_format_time_midnight():
    assert format_time(datetime(2026, 5, 1, 0, 0)) == "00:00"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_utils.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Implement utils.py**

```python
from datetime import datetime
import pytz

KYIV_TZ = pytz.timezone("Europe/Kyiv")

MONTH_NAMES_UK = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}


def now_kyiv() -> datetime:
    return datetime.now(KYIV_TZ)


def format_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y")


def format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def get_month_sheet_name(dt: datetime) -> str:
    return f"{MONTH_NAMES_UK[dt.month]} {dt.year}"


def calculate_hours_worked(arrival_str: str, departure_str: str) -> str:
    fmt = "%H:%M"
    arrival = datetime.strptime(arrival_str, fmt)
    departure = datetime.strptime(departure_str, fmt)
    total_minutes = int((departure - arrival).total_seconds() / 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours} год {minutes} хв"


def validate_full_name(name: str) -> bool:
    parts = name.strip().split()
    return len(parts) >= 2 and all(len(p) >= 2 for p in parts)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_utils.py -v
```

Expected: 13 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add utility functions with tests"
```

---

## Task 4: services/sheets.py (TDD for pure logic)

**Files:**
- Create: `services/sheets.py`
- Create: `tests/test_sheets_logic.py`

- [ ] **Step 1: Write failing tests for the pure summary function**

Create `tests/test_sheets_logic.py`:

```python
from services.sheets import _calculate_summary_from_values


def test_empty_sheet_returns_empty():
    data = [["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"]]
    assert _calculate_summary_from_values(data) == []


def test_single_worker_single_day():
    data = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.05.2026", "Владимирська Тетяна", "09:00", "18:00", "9 год 0 хв"],
    ]
    result = _calculate_summary_from_values(data)
    assert result == [("Владимирська Тетяна", 540)]


def test_two_workers_sorted_descending():
    data = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.05.2026", "Владимирська Тетяна", "09:00", "18:00", "9 год 0 хв"],
        ["01.05.2026", "Іваненко Олена", "09:15", "17:15", "8 год 0 хв"],
        ["02.05.2026", "Іваненко Олена", "09:00", "19:00", "10 год 0 хв"],
    ]
    result = _calculate_summary_from_values(data)
    assert result[0] == ("Іваненко Олена", 1080)   # 18 hours
    assert result[1] == ("Владимирська Тетяна", 540)  # 9 hours


def test_incomplete_rows_are_skipped():
    data = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.05.2026", "Владимирська Тетяна", "09:00", "", ""],
        ["01.05.2026", "Іваненко Олена", "09:15", "17:15", "8 год 0 хв"],
    ]
    result = _calculate_summary_from_values(data)
    assert len(result) == 1
    assert result[0][0] == "Іваненко Олена"


def test_accumulates_multiple_days_for_same_worker():
    data = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.05.2026", "Владимирська Тетяна", "09:00", "18:00", "9 год 0 хв"],
        ["02.05.2026", "Владимирська Тетяна", "09:00", "18:30", "9 год 30 хв"],
    ]
    result = _calculate_summary_from_values(data)
    assert result == [("Владимирська Тетяна", 1110)]  # 18h 30min = 1110 min
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_sheets_logic.py -v
```

Expected: `ImportError: cannot import name '_calculate_summary_from_values'`

- [ ] **Step 3: Create services/sheets.py**

```python
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS_PATH
from utils import format_date, get_month_sheet_name, now_kyiv, calculate_hours_worked

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

USERS_SHEET = "users"
ATTENDANCE_HEADERS = ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"]
SUMMARY_HEADERS = ["Ім'я Прізвище", "Всього годин"]


def _get_col(row: list, idx: int) -> str:
    return row[idx] if idx < len(row) else ""


def _calculate_summary_from_values(all_values: list[list]) -> list[tuple[str, int]]:
    """Pure function: given sheet rows (with header at index 0),
    return list of (name, total_minutes) sorted descending by minutes."""
    totals: dict[str, int] = {}
    for row in all_values[1:]:
        name = _get_col(row, 1)
        hours_str = _get_col(row, 4)
        if not name or not hours_str:
            continue
        try:
            parts = hours_str.split()
            hours = int(parts[0])
            minutes = int(parts[2])
            totals[name] = totals.get(name, 0) + hours * 60 + minutes
        except (IndexError, ValueError):
            continue
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_spreadsheet() -> gspread.Spreadsheet:
    return _get_client().open_by_key(SPREADSHEET_ID)


def _get_or_create_users_sheet() -> gspread.Worksheet:
    ss = _get_spreadsheet()
    try:
        return ss.worksheet(USERS_SHEET)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(USERS_SHEET, rows=1000, cols=3)
        ws.append_row(["Telegram ID", "Ім'я Прізвище", "Дата реєстрації"])
        return ws


def get_or_create_monthly_sheet(dt: datetime) -> gspread.Worksheet:
    ss = _get_spreadsheet()
    sheet_name = get_month_sheet_name(dt)
    try:
        return ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(sheet_name, rows=1000, cols=10)
        ws.update("A1:E1", [ATTENDANCE_HEADERS])
        ws.update("G1:H1", [SUMMARY_HEADERS])
        return ws


# --- User operations ---

def get_user(telegram_id: int) -> dict | None:
    ws = _get_or_create_users_sheet()
    for record in ws.get_all_records():
        if str(record["Telegram ID"]) == str(telegram_id):
            return record
    return None


def register_user(telegram_id: int, name: str) -> None:
    ws = _get_or_create_users_sheet()
    ws.append_row([str(telegram_id), name, format_date(now_kyiv())])


def get_all_workers() -> list[dict]:
    return _get_or_create_users_sheet().get_all_records()


def rename_worker(telegram_id: int, new_name: str) -> bool:
    ws = _get_or_create_users_sheet()
    for i, record in enumerate(ws.get_all_records(), start=2):
        if str(record["Telegram ID"]) == str(telegram_id):
            ws.update_cell(i, 2, new_name)
            return True
    return False


def delete_worker(telegram_id: int) -> bool:
    ws = _get_or_create_users_sheet()
    for i, record in enumerate(ws.get_all_records(), start=2):
        if str(record["Telegram ID"]) == str(telegram_id):
            ws.delete_rows(i)
            return True
    return False


# --- Attendance operations ---

def get_today_checkin(telegram_id: int) -> dict | None:
    """Return today's attendance record for this worker, or None."""
    now = now_kyiv()
    today_str = format_date(now)
    user = get_user(telegram_id)
    if not user:
        return None
    name = user["Ім'я Прізвище"]
    ws = get_or_create_monthly_sheet(now)
    for record in ws.get_all_records():
        if record.get("Дата") == today_str and record.get("Ім'я Прізвище") == name:
            return record
    return None


def has_checked_out_today(telegram_id: int) -> bool:
    record = get_today_checkin(telegram_id)
    return bool(record and record.get("Пішла"))


def append_checkin(name: str, arrival_time: str) -> None:
    now = now_kyiv()
    ws = get_or_create_monthly_sheet(now)
    ws.append_row([format_date(now), name, arrival_time, "", ""])


def update_checkout(name: str, departure_time: str, hours_worked: str) -> bool:
    now = now_kyiv()
    today_str = format_date(now)
    ws = get_or_create_monthly_sheet(now)
    all_values = ws.get_all_values()
    for i, row in enumerate(all_values):
        if (
            _get_col(row, 0) == today_str
            and _get_col(row, 1) == name
            and not _get_col(row, 3)
        ):
            ws.update_cell(i + 1, 4, departure_time)
            ws.update_cell(i + 1, 5, hours_worked)
            return True
    return False


def update_monthly_summary(dt: datetime) -> None:
    ws = get_or_create_monthly_sheet(dt)
    all_values = ws.get_all_values()
    sorted_totals = _calculate_summary_from_values(all_values)
    if not sorted_totals:
        return
    ws.batch_clear([f"G2:H{max(len(sorted_totals) + 10, 100)}"])
    summary_data = [
        [name, f"{total // 60} год {total % 60} хв"]
        for name, total in sorted_totals
    ]
    ws.update(f"G2:H{1 + len(summary_data)}", summary_data)


def get_today_attendance() -> list[dict]:
    now = now_kyiv()
    today_str = format_date(now)
    ws = get_or_create_monthly_sheet(now)
    return [r for r in ws.get_all_records() if r.get("Дата") == today_str]


def edit_record(name: str, date_str: str, field: str, new_time: str) -> bool:
    """Edit arrival ('Прийшла') or departure ('Пішла') time for a specific record."""
    day, month, year = date_str.split(".")
    dt = datetime(int(year), int(month), int(day))
    ws = get_or_create_monthly_sheet(dt)
    col = 3 if field == "Прийшла" else 4
    all_values = ws.get_all_values()
    for i, row in enumerate(all_values):
        if _get_col(row, 0) == date_str and _get_col(row, 1) == name:
            ws.update_cell(i + 1, col, new_time)
            updated = ws.row_values(i + 1)
            arrival = _get_col(updated, 2)
            departure = _get_col(updated, 3)
            if arrival and departure:
                ws.update_cell(i + 1, 5, calculate_hours_worked(arrival, departure))
            update_monthly_summary(dt)
            return True
    return False
```

- [ ] **Step 4: Run the sheets logic tests**

```bash
pytest tests/test_sheets_logic.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Run all tests to make sure nothing broke**

```bash
pytest -v
```

Expected: 18 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add services/sheets.py tests/test_sheets_logic.py
git commit -m "feat: add Google Sheets service with summary logic"
```

---

## Task 5: states.py, filters.py, keyboards/main.py

**Files:**
- Create: `states.py`
- Create: `filters.py`
- Create: `keyboards/main.py`

- [ ] **Step 1: Create states.py**

```python
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_name = State()


class AttendanceStates(StatesGroup):
    waiting_for_checkin_photo = State()
    waiting_for_checkout_photo = State()


class AdminStates(StatesGroup):
    rename_waiting_for_id = State()
    rename_waiting_for_name = State()
    delete_waiting_for_id = State()
    edit_waiting_for_name = State()
    edit_waiting_for_date = State()
    edit_waiting_for_field = State()
    edit_waiting_for_time = State()
```

- [ ] **Step 2: Create filters.py**

```python
from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import ALL_ADMIN_IDS


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ALL_ADMIN_IDS
```

- [ ] **Step 3: Create keyboards/main.py**

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add states.py filters.py keyboards/main.py
git commit -m "feat: add FSM states, admin filter, and main keyboard"
```

---

## Task 6: services/notifications.py

**Files:**
- Create: `services/notifications.py`

- [ ] **Step 1: Create services/notifications.py**

```python
from aiogram import Bot
from config import HR_ADMIN_ID


async def notify_hr_checkin(bot: Bot, name: str, time_str: str, photo_file_id: str) -> None:
    caption = f"📍 {name} прийшла на роботу о {time_str}"
    await bot.send_photo(HR_ADMIN_ID, photo=photo_file_id, caption=caption)


async def notify_hr_checkout(
    bot: Bot, name: str, time_str: str, hours_str: str, photo_file_id: str
) -> None:
    caption = f"🚪 {name} пішла з роботи о {time_str} (відпрацювала {hours_str})"
    await bot.send_photo(HR_ADMIN_ID, photo=photo_file_id, caption=caption)
```

- [ ] **Step 2: Commit**

```bash
git add services/notifications.py
git commit -m "feat: add HR notification service"
```

---

## Task 7: handlers/registration.py

**Files:**
- Create: `handlers/registration.py`

- [ ] **Step 1: Create handlers/registration.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add registration handler"
```

---

## Task 8: handlers/attendance.py

**Files:**
- Create: `handlers/attendance.py`

Note: Attendance button handlers use `StateFilter(default_state)` so they don't fire while the user is mid-way through an admin or registration FSM flow.

- [ ] **Step 1: Create handlers/attendance.py**

```python
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
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
    if sheets.get_today_checkin(message.from_user.id):
        await message.answer("❌ Ви вже зареєстровані на роботі сьогодні.")
        return
    await message.answer("📸 Надішліть фото для підтвердження приходу:")
    await state.set_state(AttendanceStates.waiting_for_checkin_photo)


@router.message(AttendanceStates.waiting_for_checkin_photo, F.photo)
async def process_checkin_photo(message: Message, state: FSMContext, bot: Bot):
    user = sheets.get_user(message.from_user.id)
    name = user["Ім'я Прізвище"]
    time_str = format_time(now_kyiv())
    photo_file_id = message.photo[-1].file_id

    sheets.append_checkin(name, time_str)
    await state.clear()
    await message.answer(
        f"✅ Ви успішно зареєстровані на роботі о {time_str}",
        reply_markup=get_main_keyboard(),
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
    if not sheets.get_today_checkin(message.from_user.id):
        await message.answer("❌ Ви ще не реєструвались на роботі сьогодні.")
        return
    if sheets.has_checked_out_today(message.from_user.id):
        await message.answer("❌ Ви вже відмітили вихід з роботи сьогодні.")
        return
    await message.answer("📸 Надішліть фото для підтвердження виходу:")
    await state.set_state(AttendanceStates.waiting_for_checkout_photo)


@router.message(AttendanceStates.waiting_for_checkout_photo, F.photo)
async def process_checkout_photo(message: Message, state: FSMContext, bot: Bot):
    user = sheets.get_user(message.from_user.id)
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
        reply_markup=get_main_keyboard(),
    )
    await notifications.notify_hr_checkout(bot, name, time_str, hours_str, photo_file_id)


@router.message(AttendanceStates.waiting_for_checkout_photo)
async def checkout_not_photo(message: Message):
    await message.answer("Будь ласка, надішліть фото (не файл і не текст).")
```

- [ ] **Step 2: Commit**

```bash
git add handlers/attendance.py
git commit -m "feat: add check-in and check-out handlers"
```

---

## Task 9: handlers/admin.py

**Files:**
- Create: `handlers/admin.py`

- [ ] **Step 1: Create handlers/admin.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add handlers/admin.py
git commit -m "feat: add admin command handlers"
```

---

## Task 10: bot.py (assembly)

**Files:**
- Create: `bot.py`

- [ ] **Step 1: Create bot.py**

```python
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import registration, attendance, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(registration.router)
    dp.include_router(attendance.router)
    dp.include_router(admin.router)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run bot locally to verify it starts**

```bash
python bot.py
```

Expected output (first few lines):
```
2026-05-22 10:00:00 INFO Bot started
```

Bot should respond to `/start` in Telegram. Press Ctrl+C to stop.

- [ ] **Step 3: Commit**

```bash
git add bot.py
git commit -m "feat: assemble bot with all routers"
```

---

## Task 11: VPS deployment

**Files:**
- Create: `veles-bot.service`

- [ ] **Step 1: Create systemd service file**

Create `veles-bot.service`:

```ini
[Unit]
Description=Veles Attendance Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/velesattendance
ExecStart=/home/ubuntu/velesattendance/venv/bin/python bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Transfer project to VPS**

Run on your local machine:
```bash
rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  /Users/Apple/IT/velesattendance/ ubuntu@YOUR_VPS_IP:/home/ubuntu/velesattendance/
```

- [ ] **Step 3: Set up Python environment on VPS**

SSH into VPS and run:
```bash
cd /home/ubuntu/velesattendance
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 4: Copy credentials and .env to VPS**

```bash
scp credentials.json ubuntu@YOUR_VPS_IP:/home/ubuntu/velesattendance/
scp .env ubuntu@YOUR_VPS_IP:/home/ubuntu/velesattendance/
```

- [ ] **Step 5: Install and start systemd service**

On VPS:
```bash
sudo cp /home/ubuntu/velesattendance/veles-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable veles-bot
sudo systemctl start veles-bot
```

- [ ] **Step 6: Verify bot is running**

```bash
sudo systemctl status veles-bot
```

Expected: `Active: active (running)`

```bash
sudo journalctl -u veles-bot -f
```

Expected: shows `Bot started` and then live logs.

- [ ] **Step 7: Commit**

```bash
git add veles-bot.service
git commit -m "feat: add systemd service for VPS deployment"
```

---

## Task 12: Google Sheets — one-time setup

Before running the bot for the first time, complete these steps manually:

- [ ] **Step 1: Create a Google Cloud project**
  1. Go to https://console.cloud.google.com
  2. Create a new project (e.g., "VelesAttendance")
  3. Enable **Google Sheets API** and **Google Drive API**

- [ ] **Step 2: Create a Service Account**
  1. Go to IAM & Admin → Service Accounts → Create
  2. Name: `veles-bot`
  3. Skip role assignment
  4. Create a JSON key → download as `credentials.json`

- [ ] **Step 3: Share the spreadsheet with the service account**
  1. Create a new Google Spreadsheet (or use existing)
  2. Copy the spreadsheet ID from its URL (the part between `/d/` and `/edit`)
  3. Click Share → paste the service account email (found in `credentials.json` as `client_email`) → give Editor access

- [ ] **Step 4: Set SPREADSHEET_ID in .env**

Open `.env` and set:
```
SPREADSHEET_ID=your_actual_spreadsheet_id_here
```

The bot will automatically create the `users` sheet and monthly sheets on first use.

---

## Smoke Test Checklist

After deployment, manually verify each flow:

- [ ] Worker sends `/start` → bot asks for name
- [ ] Worker enters "Іваненко Олена" → bot saves and shows main keyboard
- [ ] Worker sends `/start` again → bot greets by name, shows keyboard
- [ ] Worker presses "✅ Прийшла на роботу" → bot asks for photo
- [ ] Worker sends a photo → bot confirms arrival time; HR admin receives photo with caption
- [ ] Worker presses "✅ Прийшла на роботу" again → bot says already registered
- [ ] Worker presses "🚪 Пішла з роботи" → bot asks for photo
- [ ] Worker sends a photo → bot confirms departure + hours worked; HR admin receives photo; Google Sheet row is complete; monthly summary updated
- [ ] Admin sends `/workers` → sees list
- [ ] Admin sends `/today` → sees who is at work / who left
- [ ] Admin sends `/rename` → renames a worker
- [ ] Admin sends `/delete_worker` → removes a worker
- [ ] Admin sends `/edit_record` → corrects a time; hours recalculated; summary updated
- [ ] Non-admin tries `/workers` → message is silently ignored (no response)
- [ ] Worker sends text instead of photo when bot asks for photo → bot re-prompts
