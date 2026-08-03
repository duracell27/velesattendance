# Admin Schedule Edit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a keyboard-driven flow for all admins to add, edit, or delete any attendance record via inline keyboards, accessible through a persistent "📝 Редагувати графік" reply keyboard button.

**Architecture:** New `handlers/schedule_edit.py` router with FSM-driven inline keyboard flow; new `keyboards/schedule_edit.py` with all inline keyboard builders; three new sheets functions; `get_main_keyboard` extended with `is_admin` param; all call sites updated.

**Tech Stack:** Python 3.13, aiogram 3.13.0, gspread 6.1.2, pytest 8.1.1

## Global Constraints

- Ukrainian locale throughout: all user-facing strings in Ukrainian
- Time format: `HH:MM` (24-hour, zero-padded), date format: `DD.MM.YYYY`
- Callback data prefix: `se:` (schedule edit), max 64 bytes per Telegram limit
- All inline keyboards must include a `[❌ Скасувати]` row with `callback_data="se:cancel"`
- Run tests with: `cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/ -v`

---

### Task 1: Add `ScheduleEditStates` to `states.py`

**Files:**
- Modify: `states.py`

**Interfaces:**
- Produces: `ScheduleEditStates` with states: `choosing_action`, `choosing_month`, `choosing_worker`, `choosing_day`, `entering_arrival`, `entering_departure`, `choosing_field`, `entering_new_time`, `confirming_delete`

- [ ] **Step 1: Add the state group**

Open `states.py` and append after the existing `AdminStates` class:

```python
class ScheduleEditStates(StatesGroup):
    choosing_action = State()
    choosing_month = State()
    choosing_worker = State()
    choosing_day = State()
    entering_arrival = State()
    entering_departure = State()
    choosing_field = State()
    entering_new_time = State()
    confirming_delete = State()
```

- [ ] **Step 2: Verify import works**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && python -c "from states import ScheduleEditStates; print(list(ScheduleEditStates))"
```

Expected: prints 9 state names without error.

- [ ] **Step 3: Commit**

```bash
git add states.py
git commit -m "feat: add ScheduleEditStates FSM states"
```

---

### Task 2: New sheets functions — `get_available_months`, `get_record`, `add_record`, `delete_record`

**Files:**
- Modify: `services/sheets.py` (add 4 functions + extend import)
- Create: `tests/test_schedule_sheets.py`

**Interfaces:**
- Consumes: `MONTH_NAMES_UK` from `utils` (dict `{int: str}`, e.g. `{8: "Серпень"}`)
- Produces:
  - `get_available_months() -> list[str]` — sheet names like `"Серпень 2026"`, newest-first
  - `get_record(date_str: str, name: str) -> dict | None` — record dict or None
  - `add_record(date_str: str, name: str, arrival: str, departure: str) -> bool`
  - `delete_record(date_str: str, name: str) -> bool`

- [ ] **Step 1: Extend import in `services/sheets.py`**

Find the existing import line:
```python
from utils import format_date, get_month_sheet_name, now_kyiv, calculate_hours_worked
```

Replace with:
```python
from utils import format_date, get_month_sheet_name, now_kyiv, calculate_hours_worked, MONTH_NAMES_UK
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_schedule_sheets.py`:

```python
from unittest.mock import patch, MagicMock
from services import sheets


# --- get_available_months ---

def test_get_available_months_filters_month_sheets():
    mock_ws_aug = MagicMock(); mock_ws_aug.title = "Серпень 2026"
    mock_ws_jul = MagicMock(); mock_ws_jul.title = "Липень 2026"
    mock_ws_users = MagicMock(); mock_ws_users.title = "users"
    mock_ws_other = MagicMock(); mock_ws_other.title = "Якийсь аркуш"

    with patch.object(sheets, '_get_spreadsheet') as mock_sp:
        mock_sp.return_value.worksheets.return_value = [
            mock_ws_aug, mock_ws_jul, mock_ws_users, mock_ws_other
        ]
        result = sheets.get_available_months()

    assert "Серпень 2026" in result
    assert "Липень 2026" in result
    assert "users" not in result
    assert "Якийсь аркуш" not in result


def test_get_available_months_sorted_newest_first():
    mock_ws1 = MagicMock(); mock_ws1.title = "Липень 2026"
    mock_ws2 = MagicMock(); mock_ws2.title = "Серпень 2026"
    mock_ws3 = MagicMock(); mock_ws3.title = "Грудень 2025"

    with patch.object(sheets, '_get_spreadsheet') as mock_sp:
        mock_sp.return_value.worksheets.return_value = [mock_ws1, mock_ws2, mock_ws3]
        result = sheets.get_available_months()

    assert result == ["Серпень 2026", "Липень 2026", "Грудень 2025"]


# --- get_record ---

def test_get_record_returns_none_if_not_found():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["02.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws):
        result = sheets.get_record("03.08.2026", "Іваненко Олена")
    assert result is None


def test_get_record_returns_matching_dict():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["03.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws):
        result = sheets.get_record("03.08.2026", "Іваненко Олена")
    assert result is not None
    assert result["Прийшла"] == "09:00"
    assert result["Пішла"] == "17:00"


# --- add_record ---

def test_add_record_returns_false_if_record_exists():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["03.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws), \
         patch.object(sheets, 'update_monthly_summary'):
        result = sheets.add_record("03.08.2026", "Іваненко Олена", "09:00", "17:00")
    assert result is False
    mock_ws.append_rows.assert_not_called()


def test_add_record_appends_row_and_updates_summary():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws), \
         patch.object(sheets, 'update_monthly_summary') as mock_update:
        result = sheets.add_record("03.08.2026", "Іваненко Олена", "09:00", "17:00")
    assert result is True
    mock_ws.append_rows.assert_called_once_with(
        [["03.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"]],
        table_range="A1",
    )
    mock_update.assert_called_once()


# --- delete_record ---

def test_delete_record_returns_false_if_not_found():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws):
        result = sheets.delete_record("03.08.2026", "Іваненко Олена")
    assert result is False
    mock_ws.delete_rows.assert_not_called()


def test_delete_record_deletes_correct_row_and_updates_summary():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["03.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
    ]
    with patch.object(sheets, 'get_or_create_monthly_sheet', return_value=mock_ws), \
         patch.object(sheets, 'update_monthly_summary') as mock_update:
        result = sheets.delete_record("03.08.2026", "Іваненко Олена")
    assert result is True
    mock_ws.delete_rows.assert_called_once_with(2)  # row 1 (0-based) → 2 (1-based, gspread)
    mock_update.assert_called_once()
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_schedule_sheets.py -v
```

Expected: all tests FAIL with `AttributeError` (functions don't exist yet).

- [ ] **Step 4: Implement the four functions in `services/sheets.py`**

Add after the `# --- Attendance operations ---` section (after the existing `edit_record` function):

```python
# --- Admin schedule edit operations ---

def get_available_months() -> list[str]:
    month_names = set(MONTH_NAMES_UK.values())
    month_num = {v: k for k, v in MONTH_NAMES_UK.items()}
    result = []
    for ws in _get_spreadsheet().worksheets():
        parts = ws.title.split(" ")
        if len(parts) == 2 and parts[0] in month_names and parts[1].isdigit():
            result.append(ws.title)
    return sorted(
        result,
        key=lambda t: (int(t.split()[1]), month_num[t.split()[0]]),
        reverse=True,
    )


def get_record(date_str: str, name: str) -> dict | None:
    day, month, year = date_str.split(".")
    dt = datetime(int(year), int(month), int(day))
    ws = get_or_create_monthly_sheet(dt)
    for record in _attendance_records(ws):
        if record.get("Дата") == date_str and record.get("Ім'я Прізвище") == name:
            return record
    return None


def add_record(date_str: str, name: str, arrival: str, departure: str) -> bool:
    day, month, year = date_str.split(".")
    dt = datetime(int(year), int(month), int(day))
    ws = get_or_create_monthly_sheet(dt)
    for record in _attendance_records(ws):
        if record.get("Дата") == date_str and record.get("Ім'я Прізвище") == name:
            return False
    hours_str = calculate_hours_worked(arrival, departure)
    ws.append_rows([[date_str, name, arrival, departure, hours_str]], table_range="A1")
    update_monthly_summary(dt)
    return True


def delete_record(date_str: str, name: str) -> bool:
    day, month, year = date_str.split(".")
    dt = datetime(int(year), int(month), int(day))
    ws = get_or_create_monthly_sheet(dt)
    all_values = ws.get_all_values()
    for i, row in enumerate(all_values):
        if _get_col(row, 0) == date_str and _get_col(row, 1) == name:
            ws.delete_rows(i + 1)
            update_monthly_summary(dt)
            return True
    return False
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_schedule_sheets.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 6: Run full test suite to check no regressions**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add services/sheets.py tests/test_schedule_sheets.py
git commit -m "feat: add get_available_months, get_record, add_record, delete_record to sheets"
```

---

### Task 3: Create `keyboards/schedule_edit.py`

**Files:**
- Create: `keyboards/schedule_edit.py`
- Create: `tests/test_schedule_keyboards.py`

**Interfaces:**
- Consumes: nothing from other tasks (standalone keyboard builders)
- Produces:
  - `action_keyboard() -> InlineKeyboardMarkup`
  - `month_keyboard(months: list[str]) -> InlineKeyboardMarkup`
  - `worker_keyboard(workers: list[dict]) -> InlineKeyboardMarkup` — workers is list of `{"Ім'я Прізвище": str}` dicts
  - `day_keyboard(year: int, month: int) -> InlineKeyboardMarkup`
  - `field_keyboard() -> InlineKeyboardMarkup`
  - `confirm_delete_keyboard() -> InlineKeyboardMarkup`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schedule_keyboards.py`:

```python
from keyboards.schedule_edit import (
    action_keyboard, month_keyboard, worker_keyboard,
    day_keyboard, field_keyboard, confirm_delete_keyboard,
)


def _all_callbacks(kb):
    return [btn.callback_data for row in kb.inline_keyboard for btn in row]


def _all_texts(kb):
    return [btn.text for row in kb.inline_keyboard for btn in row]


def test_action_keyboard_has_three_actions_and_cancel():
    kb = action_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:action:add" in cbs
    assert "se:action:edit" in cbs
    assert "se:action:delete" in cbs
    assert "se:cancel" in cbs


def test_month_keyboard_has_cancel_and_all_months():
    months = ["Серпень 2026", "Липень 2026"]
    kb = month_keyboard(months)
    cbs = _all_callbacks(kb)
    assert "se:month:Серпень 2026" in cbs
    assert "se:month:Липень 2026" in cbs
    assert "se:cancel" in cbs


def test_worker_keyboard_has_all_workers_and_cancel():
    workers = [
        {"Ім'я Прізвище": "Іваненко Олена"},
        {"Ім'я Прізвище": "Петренко Марія"},
    ]
    kb = worker_keyboard(workers)
    cbs = _all_callbacks(kb)
    assert "se:worker:Іваненко Олена" in cbs
    assert "se:worker:Петренко Марія" in cbs
    assert "se:cancel" in cbs


def test_day_keyboard_august_has_31_days():
    kb = day_keyboard(2026, 8)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 31
    assert "se:day:1" in day_cbs
    assert "se:day:31" in day_cbs


def test_day_keyboard_february_non_leap_has_28_days():
    kb = day_keyboard(2025, 2)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 28


def test_day_keyboard_february_leap_has_29_days():
    kb = day_keyboard(2024, 2)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 29


def test_day_keyboard_rows_have_max_5_buttons_excluding_cancel():
    kb = day_keyboard(2026, 8)
    # all rows except last (cancel row) should have ≤ 5 buttons
    for row in kb.inline_keyboard[:-1]:
        assert len(row) <= 5


def test_field_keyboard_has_pryyshla_and_pishla():
    kb = field_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:field:Прийшла" in cbs
    assert "se:field:Пішла" in cbs
    assert "se:cancel" in cbs


def test_confirm_delete_keyboard_has_confirm_and_cancel():
    kb = confirm_delete_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:confirm:yes" in cbs
    assert "se:cancel" in cbs
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_schedule_keyboards.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `keyboards/schedule_edit.py`**

Create `keyboards/schedule_edit.py`:

```python
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
    names = [w["Ім'я Прізвище"] for w in workers]
    for i in range(0, len(names), 2):
        row = [
            InlineKeyboardButton(text=n, callback_data=f"se:worker:{n}")
            for n in names[i:i + 2]
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_schedule_keyboards.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add keyboards/schedule_edit.py tests/test_schedule_keyboards.py
git commit -m "feat: add schedule_edit inline keyboard builders"
```

---

### Task 4: Update `keyboards/main.py` and all call sites

**Files:**
- Modify: `keyboards/main.py`
- Modify: `handlers/registration.py`
- Modify: `handlers/attendance.py`
- Create: `tests/test_main_keyboard.py`

**Interfaces:**
- Produces: `get_main_keyboard(checked_in=False, checked_out=False, is_admin=False) -> ReplyKeyboardMarkup` — adds "📝 Редагувати графік" row when `is_admin=True`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main_keyboard.py`:

```python
from keyboards.main import get_main_keyboard


def _all_texts(kb):
    return [btn.text for row in kb.keyboard for btn in row]


def test_admin_keyboard_has_edit_schedule_button():
    kb = get_main_keyboard(is_admin=True)
    assert "📝 Редагувати графік" in _all_texts(kb)


def test_non_admin_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard(is_admin=False)
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_default_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard()
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_admin_checked_in_keyboard_has_all_buttons():
    kb = get_main_keyboard(checked_in=True, is_admin=True)
    texts = _all_texts(kb)
    assert "🚪 Пішла з роботи" in texts
    assert "📊 Моя відвідуваність" in texts
    assert "📝 Редагувати графік" in texts
    assert "✅ Прийшла на роботу" not in texts


def test_admin_checked_out_keyboard_has_edit_button():
    kb = get_main_keyboard(checked_out=True, is_admin=True)
    texts = _all_texts(kb)
    assert "📊 Моя відвідуваність" in texts
    assert "📝 Редагувати графік" in texts
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_main_keyboard.py -v
```

Expected: admin tests FAIL (no `is_admin` param yet), default tests PASS.

- [ ] **Step 3: Update `keyboards/main.py`**

Replace the entire file content:

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard(
    checked_in: bool = False,
    checked_out: bool = False,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:
    if checked_out:
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
    if is_admin:
        buttons.append([KeyboardButton(text="📝 Редагувати графік")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, persistent=True)
```

- [ ] **Step 4: Run keyboard tests to confirm they pass**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/test_main_keyboard.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Update call sites in `handlers/registration.py`**

Add import at the top of `handlers/registration.py` (after existing imports):
```python
from config import ALL_ADMIN_IDS
```

Then update every `get_main_keyboard(...)` call in `handlers/registration.py` to pass `is_admin`:

In `cmd_start` — three calls, all need `is_admin`:
```python
# Replace the three get_main_keyboard calls in cmd_start with:
is_admin = message.from_user.id in ALL_ADMIN_IDS

# call 1 (checked_out):
reply_markup=get_main_keyboard(checked_out=True, is_admin=is_admin)

# call 2 (checked_in):
reply_markup=get_main_keyboard(checked_in=True, is_admin=is_admin)

# call 3 (default):
reply_markup=get_main_keyboard(is_admin=is_admin)
```

In `process_name` — new users are never admins, so:
```python
reply_markup=get_main_keyboard()
```
(no change needed — default `is_admin=False` is correct)

- [ ] **Step 6: Update call sites in `handlers/attendance.py`**

Add import at the top of `handlers/attendance.py` (after existing imports):
```python
from config import ALL_ADMIN_IDS
```

Then update every `get_main_keyboard(...)` call to pass `is_admin`. Each handler already has `message.from_user.id` available:

```python
# Pattern to use in every handler that calls get_main_keyboard:
is_admin = message.from_user.id in ALL_ADMIN_IDS

# Then pass is_admin to every get_main_keyboard call in that handler.
```

Specific locations:

**`checkin_button`** (2 calls):
```python
reply_markup=get_main_keyboard(checked_out=True, is_admin=message.from_user.id in ALL_ADMIN_IDS)
# and
reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS)
```

**`process_checkin_photo`** (1 call):
```python
reply_markup=get_main_keyboard(checked_in=True, is_admin=message.from_user.id in ALL_ADMIN_IDS)
```

**`checkout_button`** (2 calls):
```python
reply_markup=get_main_keyboard(is_admin=message.from_user.id in ALL_ADMIN_IDS)
# and
reply_markup=get_main_keyboard(checked_out=True, is_admin=message.from_user.id in ALL_ADMIN_IDS)
```

**`my_attendance`** (1 call, already has `is_checked_in` local var):
```python
reply_markup=get_main_keyboard(checked_in=is_checked_in, is_admin=message.from_user.id in ALL_ADMIN_IDS)
```

- [ ] **Step 7: Run full test suite**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add keyboards/main.py handlers/registration.py handlers/attendance.py tests/test_main_keyboard.py
git commit -m "feat: add is_admin param to get_main_keyboard and update all call sites"
```

---

### Task 5: Create `handlers/schedule_edit.py` and register in `bot.py`

**Files:**
- Create: `handlers/schedule_edit.py`
- Modify: `bot.py`

**Interfaces:**
- Consumes:
  - `ScheduleEditStates` from `states`
  - `sheets.get_available_months()`, `sheets.get_all_workers()`, `sheets.get_record()`, `sheets.add_record()`, `sheets.delete_record()`, `sheets.edit_record()`
  - `action_keyboard`, `month_keyboard`, `worker_keyboard`, `day_keyboard`, `field_keyboard`, `confirm_delete_keyboard` from `keyboards.schedule_edit`
  - `MONTH_NAMES_UK` from `utils`
  - `ALL_ADMIN_IDS` from `config`
  - `calculate_hours_worked` from `utils`
- Produces: `router` (aiogram Router) — registered in `bot.py` before `admin.router`

- [ ] **Step 1: Create `handlers/schedule_edit.py`**

```python
import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from services import sheets
from states import ScheduleEditStates
from filters import IsAdmin
from keyboards.schedule_edit import (
    action_keyboard, month_keyboard, worker_keyboard,
    day_keyboard, field_keyboard, confirm_delete_keyboard,
)
from utils import MONTH_NAMES_UK, calculate_hours_worked

router = Router()
router.message.filter(IsAdmin())

_MONTH_NUM = {name: num for num, name in MONTH_NAMES_UK.items()}

TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _parse_sheet_name(sheet_name: str) -> tuple[int, int]:
    """Return (year, month_number) from 'Серпень 2026'."""
    name, year = sheet_name.split(" ")
    return int(year), _MONTH_NUM[name]


def _build_date_str(sheet_name: str, day: int) -> str:
    year, month = _parse_sheet_name(sheet_name)
    return f"{day:02d}.{month:02d}.{year}"


# ── Entry point ──────────────────────────────────────────────────────────────

@router.message(F.text == "📝 Редагувати графік", StateFilter(default_state))
async def schedule_edit_start(message: Message, state: FSMContext):
    await message.answer("Оберіть дію:", reply_markup=action_keyboard())
    await state.set_state(ScheduleEditStates.choosing_action)


# ── Cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), StateFilter(ScheduleEditStates))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.")


@router.callback_query(F.data == "se:cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Скасовано.")
    await callback.answer()


# ── Step 1: Action ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:action:"), StateFilter(ScheduleEditStates.choosing_action))
async def action_selected(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":", 2)[2]
    await state.update_data(action=action)
    months = sheets.get_available_months()
    if not months:
        await callback.message.edit_text("❌ Немає доступних місяців в таблиці.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text("Виберіть місяць:", reply_markup=month_keyboard(months))
    await state.set_state(ScheduleEditStates.choosing_month)
    await callback.answer()


# ── Step 2: Month ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:month:"), StateFilter(ScheduleEditStates.choosing_month))
async def month_selected(callback: CallbackQuery, state: FSMContext):
    sheet_name = callback.data.split(":", 2)[2]
    await state.update_data(sheet_name=sheet_name)
    workers = sheets.get_all_workers()
    if not workers:
        await callback.message.edit_text("❌ Немає зареєстрованих працівників.")
        await state.clear()
        await callback.answer()
        return
    await callback.message.edit_text("Виберіть працівника:", reply_markup=worker_keyboard(workers))
    await state.set_state(ScheduleEditStates.choosing_worker)
    await callback.answer()


# ── Step 3: Worker ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:worker:"), StateFilter(ScheduleEditStates.choosing_worker))
async def worker_selected(callback: CallbackQuery, state: FSMContext):
    worker_name = callback.data.split(":", 2)[2]
    await state.update_data(worker_name=worker_name)
    data = await state.get_data()
    year, month = _parse_sheet_name(data["sheet_name"])
    await callback.message.edit_text(
        "Виберіть число:", reply_markup=day_keyboard(year, month)
    )
    await state.set_state(ScheduleEditStates.choosing_day)
    await callback.answer()


# ── Step 4: Day → branch by action ───────────────────────────────────────────

@router.callback_query(F.data.startswith("se:day:"), StateFilter(ScheduleEditStates.choosing_day))
async def day_selected(callback: CallbackQuery, state: FSMContext):
    day = int(callback.data.split(":", 2)[2])
    await state.update_data(day=day)
    data = await state.get_data()
    action = data["action"]
    date_str = _build_date_str(data["sheet_name"], day)

    if action == "add":
        await callback.message.edit_text(
            f"➕ Додавання: {data['worker_name']}, {date_str}\n\n"
            "Введіть час приходу (ГГ:ХХ):"
        )
        await state.set_state(ScheduleEditStates.entering_arrival)

    elif action == "edit":
        await callback.message.edit_text(
            f"✏️ Редагування: {data['worker_name']}, {date_str}\n\nЩо редагуємо?",
            reply_markup=field_keyboard(),
        )
        await state.set_state(ScheduleEditStates.choosing_field)

    elif action == "delete":
        record = sheets.get_record(date_str, data["worker_name"])
        if record:
            info = (
                f"📅 {date_str}  👤 {data['worker_name']}\n"
                f"🕐 Прийшла: {record.get('Прийшла', '—')}\n"
                f"🕐 Пішла: {record.get('Пішла', '—')}\n"
                f"⏱ Відпрацьовано: {record.get('Відпрацьовано', '—')}"
            )
        else:
            info = f"📅 {date_str}  👤 {data['worker_name']}\n(запис не знайдено)"
        await callback.message.edit_text(
            f"🗑 Видалення запису:\n\n{info}\n\nПідтвердити?",
            reply_markup=confirm_delete_keyboard(),
        )
        await state.set_state(ScheduleEditStates.confirming_delete)

    await callback.answer()


# ── Add: arrival ─────────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_arrival))
async def enter_arrival(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 09:05):")
        return
    await state.update_data(arrival=time_str)
    await message.answer("Введіть час виходу (ГГ:ХХ):")
    await state.set_state(ScheduleEditStates.entering_departure)


# ── Add: departure ───────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_departure))
async def enter_departure(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 17:00):")
        return
    data = await state.get_data()
    arr_h, arr_m = map(int, data["arrival"].split(":"))
    dep_h, dep_m = map(int, time_str.split(":"))
    if dep_h * 60 + dep_m <= arr_h * 60 + arr_m:
        await message.answer(
            "❌ Час виходу не може бути раніше або рівним часу приходу. Введіть знову:"
        )
        return
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.add_record(date_str, data["worker_name"], data["arrival"], time_str)
    await state.clear()
    if success:
        hours = calculate_hours_worked(data["arrival"], time_str)
        await message.answer(
            f"✅ Запис додано:\n{data['worker_name']}, {date_str}\n"
            f"Прийшла: {data['arrival']}, Пішла: {time_str}, Відпрацьовано: {hours}"
        )
    else:
        await message.answer("❌ Запис за цю дату вже існує.")


# ── Edit: field selection ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("se:field:"), StateFilter(ScheduleEditStates.choosing_field))
async def field_selected(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 2)[2]
    await state.update_data(field=field)
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    await callback.message.edit_text(
        f"✏️ {data['worker_name']}, {date_str} — {field}\n\nВведіть новий час (ГГ:ХХ):"
    )
    await state.set_state(ScheduleEditStates.entering_new_time)
    await callback.answer()


# ── Edit: new time ────────────────────────────────────────────────────────────

@router.message(StateFilter(ScheduleEditStates.entering_new_time))
async def enter_new_time(message: Message, state: FSMContext):
    time_str = message.text.strip() if message.text else ""
    if not TIME_RE.match(time_str):
        await message.answer("Невірний формат. Введіть час ГГ:ХХ (наприклад: 09:05):")
        return
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.edit_record(data["worker_name"], date_str, data["field"], time_str)
    await state.clear()
    if success:
        await message.answer(
            f"✅ Оновлено: {data['worker_name']}, {date_str}\n"
            f"{data['field']} → {time_str}"
        )
    else:
        await message.answer("❌ Запис не знайдено.")


# ── Delete: confirmed ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "se:confirm:yes", StateFilter(ScheduleEditStates.confirming_delete))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_str = _build_date_str(data["sheet_name"], data["day"])
    success = sheets.delete_record(date_str, data["worker_name"])
    await state.clear()
    if success:
        await callback.message.edit_text(
            f"✅ Видалено: {data['worker_name']}, {date_str}"
        )
    else:
        await callback.message.edit_text("❌ Запис не знайдено.")
    await callback.answer()
```

- [ ] **Step 2: Register the router in `bot.py`**

Add import after existing handler imports:
```python
from handlers import registration, attendance, admin, schedule_edit
```

Add router inclusion **before** `admin.router`:
```python
dp.include_router(schedule_edit.router)
dp.include_router(admin.router)
```

The final include block should look like:
```python
dp.include_router(registration.router)
dp.include_router(attendance.router)
dp.include_router(schedule_edit.router)
dp.include_router(admin.router)
```

- [ ] **Step 3: Verify import resolves without errors**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && python -c "from handlers import schedule_edit; print('OK')"
```

Expected: prints `OK` with no errors.

- [ ] **Step 4: Run full test suite**

```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Manual smoke test**

Start the bot:
```bash
cd /Users/Apple/IT/velesattendance && source venv/bin/activate && python bot.py
```

Check as admin user:
1. Send `/start` → keyboard must show "📝 Редагувати графік" button
2. Press "📝 Редагувати графік" → bot sends inline keyboard with [➕ Додати] [✏️ Редагувати] [🗑 Видалити] [❌ Скасувати]
3. **Add flow:** Додати → select month → select worker → select day → enter arrival (e.g. `09:00`) → enter departure (e.g. `17:00`) → "✅ Запис додано"
4. **Edit flow:** Редагувати → month → worker → day → [Прийшла/Пішла] → new time → "✅ Оновлено"
5. **Delete flow:** Видалити → month → worker → day → shows record → [Так, видалити] → "✅ Видалено"
6. **Cancel:** Press ❌ Скасувати at any step → "Скасовано."
7. **Error — add duplicate:** Try adding a record for a date that already has one → "❌ Запис за цю дату вже існує"
8. **Error — bad time:** Enter `9:5` → "Невірний формат..."
9. **Error — departure before arrival:** Enter arrival `17:00`, departure `09:00` → "❌ Час виходу не може бути раніше..."

Check as non-admin user:
- Send `/start` → keyboard must NOT show "📝 Редагувати графік"

- [ ] **Step 6: Commit**

```bash
git add handlers/schedule_edit.py bot.py
git commit -m "feat: add admin schedule edit handler with full add/edit/delete flow"
```
