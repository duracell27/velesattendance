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


_spreadsheet: gspread.Spreadsheet | None = None
_worksheets: dict[str, gspread.Worksheet] = {}


def _get_spreadsheet() -> gspread.Spreadsheet:
    global _spreadsheet
    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        _spreadsheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
    return _spreadsheet


def _get_worksheet(name: str) -> gspread.Worksheet | None:
    if name not in _worksheets:
        try:
            _worksheets[name] = _get_spreadsheet().worksheet(name)
        except gspread.WorksheetNotFound:
            return None
    return _worksheets[name]


def _get_or_create_users_sheet() -> gspread.Worksheet:
    ws = _get_worksheet(USERS_SHEET)
    if ws is None:
        ws = _get_spreadsheet().add_worksheet(USERS_SHEET, rows=1000, cols=3)
        ws.append_row(["Telegram ID", "Ім'я Прізвище", "Дата реєстрації"])
        _worksheets[USERS_SHEET] = ws
    return ws


def get_or_create_monthly_sheet(dt: datetime) -> gspread.Worksheet:
    sheet_name = get_month_sheet_name(dt)
    ws = _get_worksheet(sheet_name)
    if ws is None:
        ws = _get_spreadsheet().add_worksheet(sheet_name, rows=1000, cols=10)
        ws.update("A1:E1", [ATTENDANCE_HEADERS])
        ws.update("G1:H1", [SUMMARY_HEADERS])
        _worksheets[sheet_name] = ws
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

def _attendance_records(ws: gspread.Worksheet) -> list[dict]:
    """Read only attendance columns (A-E), avoiding duplicate header in summary column G."""
    all_values = ws.get_all_values()
    if not all_values:
        return []
    headers = all_values[0][:5]
    return [dict(zip(headers, row[:5])) for row in all_values[1:] if any(row[:5])]


def get_today_checkin(telegram_id: int) -> dict | None:
    """Return today's attendance record for this worker, or None."""
    now = now_kyiv()
    today_str = format_date(now)
    user = get_user(telegram_id)
    if not user:
        return None
    name = user["Ім'я Прізвище"]
    ws = get_or_create_monthly_sheet(now)
    for record in _attendance_records(ws):
        if record.get("Дата") == today_str and record.get("Ім'я Прізвище") == name:
            return record
    return None


def has_checked_out_today(telegram_id: int) -> bool:
    record = get_today_checkin(telegram_id)
    return bool(record and record.get("Пішла"))


def append_checkin(name: str, arrival_time: str) -> None:
    now = now_kyiv()
    ws = get_or_create_monthly_sheet(now)
    ws.append_rows([[format_date(now), name, arrival_time, "", ""]], table_range="A1")


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
    return [r for r in _attendance_records(ws) if r.get("Дата") == today_str]


def edit_record(name: str, date_str: str, field: str, new_time: str) -> bool:
    """Edit arrival ('Прийшла') or departure ('Пішла') time for a specific record."""
    day, month, year = date_str.split(".")
    try:
        dt = datetime(int(year), int(month), int(day))
    except ValueError:
        return False
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
