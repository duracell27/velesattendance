# Admin Schedule Edit — Design Spec
**Date:** 2026-08-03

## Overview

Add a keyboard-driven flow for all admins to add, edit, or delete attendance records in Google Sheets. Replaces the existing text-only `/edit_record` command with a fully inline-keyboard UX.

---

## Architecture

| File | Change |
|---|---|
| `keyboards/main.py` | Add `is_admin: bool = False` param → appends "📝 Редагувати графік" button when True |
| `keyboards/schedule_edit.py` | **New**: inline keyboard builders for each step |
| `handlers/schedule_edit.py` | **New**: router with callback + message handlers for the full flow |
| `states.py` | Add `ScheduleEditStates` |
| `services/sheets.py` | Add `get_available_months`, `add_record`, `delete_record` |
| `bot.py` | Include new router |
| `handlers/registration.py` + `handlers/attendance.py` | Pass `is_admin=True` to `get_main_keyboard()` for admin users |

---

## FSM States (`ScheduleEditStates`)

```
choosing_action
choosing_month
choosing_worker
choosing_day
entering_arrival
entering_departure
choosing_field
entering_new_time
confirming_delete
```

---

## Full Flow

```
[Reply button: "📝 Редагувати графік"]
    → inline keyboard: [Додати] [Редагувати] [Видалити] [Скасувати]
    → State: choosing_action

[Callback: action selected]
    → inline keyboard: existing month sheets (e.g. "Серпень 2026", "Липень 2026")
    → State: choosing_month

[Callback: month selected]
    → inline keyboard: all registered workers (name buttons)
    → State: choosing_worker

[Callback: worker selected]
    → inline keyboard: days 1..N of the selected month (5 per row)
    → State: choosing_day

[Callback: day selected]
    ├── Додати
    │   → "Введіть час приходу (ГГ:ХХ):" → State: entering_arrival
    │   → validate HH:MM → "Введіть час виходу (ГГ:ХХ):" → State: entering_departure
    │   → validate HH:MM, check departure > arrival
    │   → sheets.add_record(...) → recalculate summary → "✅ Запис додано"
    │   → State: clear
    │
    ├── Редагувати
    │   → inline keyboard: [Прийшла] [Пішла] [Скасувати] → State: choosing_field
    │   → "Введіть новий час (ГГ:ХХ):" → State: entering_new_time
    │   → validate HH:MM → sheets.edit_record(...) → recalculate summary → "✅ Оновлено"
    │   → State: clear
    │
    └── Видалити
        → show existing record text + inline: [✅ Так, видалити] [❌ Скасувати]
        → State: confirming_delete
        → [Так] → sheets.delete_record(...) → recalculate summary → "✅ Видалено"
        → State: clear
```

---

## New `sheets.py` Functions

### `get_available_months() -> list[str]`
Returns worksheet names matching the pattern `"<UkrMonth> <YYYY>"`, sorted newest-first. Used to populate the month selection keyboard.

### `add_record(sheet_name, date_str, name, arrival, departure) -> bool`
- Checks if a record already exists for that date+name; returns `False` if so.
- Appends new row: `[date_str, name, arrival, departure, hours_worked]`.
- Calls `update_monthly_summary(dt)`.
- Returns `True` on success.

### `delete_record(sheet_name, date_str, name) -> bool`
- Finds the row matching date+name; returns `False` if not found.
- Deletes the row.
- Calls `update_monthly_summary(dt)`.
- Returns `True` on success.

### Existing: `edit_record(name, date_str, field, new_time) -> bool`
Unchanged. Still called internally by the new edit flow.

---

## `keyboards/schedule_edit.py` — Keyboard Builders

```python
action_keyboard() -> InlineKeyboardMarkup
    # [Додати] [Редагувати] [Видалити]
    # [Скасувати]

month_keyboard(months: list[str]) -> InlineKeyboardMarkup
    # one button per month + [Скасувати]

worker_keyboard(workers: list[dict]) -> InlineKeyboardMarkup
    # one button per worker (name) + [Скасувати]

day_keyboard(year: int, month: int) -> InlineKeyboardMarkup
    # days 1..N (5 per row) + [Скасувати]

field_keyboard() -> InlineKeyboardMarkup
    # [Прийшла] [Пішла] [Скасувати]

confirm_delete_keyboard() -> InlineKeyboardMarkup
    # [✅ Так, видалити] [❌ Скасувати]
```

Callback data format: `"se:<step>:<value>"` (e.g. `"se:action:add"`, `"se:month:Серпень 2026"`, `"se:day:15"`).

---

## Admin Keyboard

`get_main_keyboard(checked_in, checked_out, is_admin)`:
- `is_admin=True` appends "📝 Редагувати графік" as the last row.
- All call sites in `registration.py` and `attendance.py` pass `is_admin=(user_id in ALL_ADMIN_IDS)`.

---

## Error Handling

| Scenario | Response |
|---|---|
| Add: record already exists for date+worker | "❌ Запис за цю дату вже існує" |
| Edit/Delete: record not found | "❌ Запис не знайдено" |
| Invalid time format | Re-prompt: "Невірний формат. Введіть час ГГ:ХХ (наприклад: 09:05):" |
| Departure ≤ arrival | "❌ Час виходу не може бути раніше або рівним часу приходу" |
| `/cancel` command at any state | Clear state → "Скасовано." |
| [Скасувати] inline button | Clear state → "Скасовано." |

---

## Out of Scope

- Editing the "Відпрацьовано" column directly (always auto-calculated).
- Removing the existing `/edit_record` command (left as-is for now).
- Pagination for large worker or day lists.
