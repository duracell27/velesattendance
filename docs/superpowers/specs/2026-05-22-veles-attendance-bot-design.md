# Veles Attendance Bot — Design Spec
**Date:** 2026-05-22

## Overview

Telegram bot for tracking employee work attendance. Workers check in and out via two buttons. All data is recorded in Google Sheets. HR admin receives photo confirmations. Regular admins can view stats and manage workers.

---

## Tech Stack

- **Language:** Python 3.11+
- **Telegram library:** aiogram 3.x (async, polling mode)
- **Google Sheets:** gspread (service account auth)
- **FSM storage:** MemoryStorage (built-in aiogram, ephemeral — acceptable since state is temporary)
- **Hosting:** VPS, managed via systemd
- **Timezone:** Europe/Kyiv (UTC+3)

---

## Google Sheets Structure

### Sheet: "users"
Stores registered workers.

| Telegram ID | Ім'я Прізвище | Дата реєстрації |
|-------------|---------------|-----------------|
| 123456789   | Владимирська Тетяна | 01.05.2026 |

### Monthly sheets (e.g. "Травень 2026")
Created automatically when the first record of a new month is written.

**Left side — attendance log (columns A–E):**

| Дата | Ім'я Прізвище | Прийшла | Пішла | Відпрацьовано |
|------|--------------|---------|-------|---------------|
| 01.05.2026 | Владимирська Тетяна | 09:00 | 18:00 | 9 год 0 хв |
| 01.05.2026 | Іваненко Олена | 09:15 | 17:45 | 8 год 30 хв |

Rows are appended chronologically. A new pair of rows is added each day per worker on shift.

**Right side — monthly summary (columns G–H, separated by one empty column):**

| Ім'я Прізвище | Всього годин |
|--------------|-------------|
| Владимирська Тетяна | 47 год 20 хв |
| Іваненко Олена | 38 год 15 хв |

- Sorted descending by total hours.
- Recalculated and rewritten after every check-out event.

---

## Bot Flows

### Registration (`/start`)
1. Bot checks if Telegram ID exists in "users" sheet.
2. If new: bot asks for full name with example — *"Введіть ваше ім'я та прізвище, наприклад: Владимирська Тетяна"*
3. Name is saved to "users" sheet.
4. Main menu is shown.

If already registered: main menu is shown directly.

### Main Menu (Reply Keyboard)
```
✅ Прийшла на роботу
🚪 Пішла з роботи
```

### Flow: "Прийшла на роботу"
1. Check if a check-in record already exists for today → if yes, reply with error message, stop.
2. Bot asks for a photo.
3. On photo received:
   - Append row to monthly sheet: date, name, arrival time (departure and hours left empty).
   - Reply to worker: `✅ Ви успішно зареєстровані на роботі о 09:05`
   - Forward photo to HR admin with caption: `📍 Владимирська Тетяна прийшла на роботу о 09:05`

### Flow: "Пішла з роботи"
1. Check if a check-in record exists for today → if no, reply with error message, stop.
2. Check if already checked out today → if yes, reply with error, stop.
3. Bot asks for a photo.
4. On photo received:
   - Update existing row: fill departure time, calculate and fill hours worked.
   - Recalculate and rewrite monthly summary (columns G–H).
   - Reply to worker: `✅ До побачення! Ви пішли з роботи о 18:10. Відпрацьовано: 9 год 5 хв`
   - Forward photo to HR admin with caption: `🚪 Владимирська Тетяна пішла з роботи о 18:10 (відпрацювала 9 год 5 хв)`

---

## Admin Roles

### HR Admin
- Receives forwarded worker photos with captions (check-in and check-out events).
- Has access to all regular admin commands.
- ID configured in `config.py`.

### Regular Admins
- Do NOT receive photos.
- Have access to admin commands.
- IDs configured in `config.py`.

### Admin Commands
| Command | Description |
|---------|-------------|
| `/workers` | List all registered workers (name + Telegram ID) |
| `/today` | Who is currently at work / who has already left today |
| `/rename` | Rename a worker (by Telegram ID) |
| `/delete_worker` | Remove a worker from the registry |
| `/edit_record` | Correct a check-in or check-out time for a specific record |

---

## Project Structure

```
velesattendance/
├── bot.py                  # entry point, starts polling
├── config.py               # bot token, admin IDs, spreadsheet ID
├── states.py               # FSM states (waiting for photo, name)
├── handlers/
│   ├── __init__.py
│   ├── registration.py     # /start, name input
│   ├── attendance.py       # check-in / check-out + photo handling
│   └── admin.py            # admin commands
├── services/
│   ├── __init__.py
│   ├── sheets.py           # all Google Sheets operations
│   └── notifications.py    # photo forwarding to HR admin
├── keyboards/
│   ├── __init__.py
│   └── main.py             # main reply keyboard
├── .env                    # bot token, path to Google credentials JSON
├── requirements.txt
└── veles-bot.service       # systemd unit for auto-start on VPS
```

---

## Configuration Inputs Required from Owner

| Item | Description |
|------|-------------|
| Telegram Bot Token | From @BotFather |
| HR Admin Telegram ID | Receives photos |
| Regular Admin Telegram IDs | One or more, comma-separated in config |
| Google Spreadsheet ID | From the spreadsheet URL |
| Google Service Account JSON | Downloaded from Google Cloud Console |

---

## Deployment

- VPS with Python 3.11+
- Google Service Account JSON placed on server (path referenced in `.env`)
- Bot registered as a systemd service (`veles-bot.service`) for auto-start on reboot
- No nginx, no SSL required (polling mode)
