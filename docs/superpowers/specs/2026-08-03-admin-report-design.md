# Admin Attendance Report — Design Spec
**Date:** 2026-08-03

## Overview

Admins do not have their own attendance. When an admin presses the keyboard button, they see a month → worker selection flow and then a formatted attendance report identical to what a regular worker sees for themselves. The button text changes to "📊 Звіт відвідуваності" for admins; regular users keep "📊 Моя відвідуваність".

---

## Architecture

| File | Change |
|---|---|
| `keyboards/main.py` | Admin keyboard: replace checkin/checkout/my-attendance buttons with just two buttons — "📊 Звіт відвідуваності" and "📝 Редагувати графік" |
| `states.py` | Add `AdminReportStates` with `choosing_month`, `choosing_worker` |
| `services/sheets.py` | Add `get_attendance_by_name_and_month(name, sheet_name) -> list[dict]` |
| `keyboards/admin_report.py` | **New**: inline keyboard builders (month, worker, cancel) |
| `handlers/admin_report.py` | **New**: router with `IsAdmin()` filter, full flow |
| `bot.py` | Include new router before `admin.router` |

---

## Admin Keyboard Layout

When `is_admin=True`, `get_main_keyboard` ignores `checked_in`/`checked_out` and always returns:

```
[📊 Звіт відвідуваності]
[📝 Редагувати графік]
```

Regular user keyboard is unchanged.

---

## FSM States (`AdminReportStates`)

```
choosing_month
choosing_worker
```

---

## Flow

```
[Reply button: "📊 Звіт відвідуваності"]
    → inline keyboard: existing month sheets (newest-first)
    → State: choosing_month

[Callback: ar:month:<name>]
    → inline keyboard: all registered workers (index-based: ar:worker:0, ar:worker:1 …)
    → State: choosing_worker

[Callback: ar:worker:<idx>]
    → fetch attendance via get_attendance_by_name_and_month(name, sheet_name)
    → render report text (same format as my_attendance)
    → State: clear

[Callback: ar:cancel at any step]
    → State: clear → "Скасовано."
```

---

## Report Format

```
📊 <b>Відвідуваність Іваненко Олена — Серпень 2026:</b>

📅 01.08.2026 | 09:00 - 17:30 | 8 год 30 хв
📅 02.08.2026 | 09:15 - ... | ⏳ в процесі
📅 03.08.2026 | 09:00 - — | не завершено

<b>Загалом за місяць: 42 год 30 хв</b>
```

- Completed rows (has Пішла + Відпрацьовано): show full line, add minutes to total
- Today + no checkout: show "⏳ в процесі"
- Other incomplete: show "не завершено"
- No records at all: "📊 Немає записів за цей місяць."

---

## New `sheets.py` Function

```python
def get_attendance_by_name_and_month(name: str, sheet_name: str) -> list[dict]:
    ws = _get_worksheet(sheet_name)
    if ws is None:
        return []
    return [r for r in _attendance_records(ws) if r.get("Ім'я Прізвище") == name]
```

---

## `keyboards/admin_report.py` — Builders

```python
ar_month_keyboard(months: list[str]) -> InlineKeyboardMarkup
    # one button per month (ar:month:<name>) + [❌ Скасувати] (ar:cancel)

ar_worker_keyboard(workers: list[dict]) -> InlineKeyboardMarkup
    # index-based (ar:worker:0, ar:worker:1 …), 2 per row + [❌ Скасувати]
```

Callback data prefix: `"ar:"`. Worker buttons use index (not name) to stay within Telegram's 64-byte limit.

---

## Error Handling

| Scenario | Response |
|---|---|
| No months available | "❌ Немає доступних місяців в таблиці." → clear state |
| No workers registered | "❌ Немає зареєстрованих працівників." → clear state |
| No records for worker+month | "📊 Немає записів за цей місяць." |
| `ar:cancel` callback | Clear state → "Скасовано." |

---

## Out of Scope

- Admins viewing their own attendance (admins have no attendance records)
- Pagination for large result sets
- Exporting reports
