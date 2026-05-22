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
