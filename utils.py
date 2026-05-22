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
