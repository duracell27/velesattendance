from unittest.mock import patch, MagicMock
from services import sheets


def test_returns_matching_records_only():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
        ["01.08.2026", "Петренко Марія", "09:15", "17:15", "8 год 0 хв"],
    ]
    with patch.object(sheets, '_get_worksheet', return_value=mock_ws):
        result = sheets.get_attendance_by_name_and_month("Іваненко Олена", "Серпень 2026")
    assert len(result) == 1
    assert result[0]["Дата"] == "01.08.2026"
    assert result[0]["Прийшла"] == "09:00"


def test_returns_empty_when_no_match():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.08.2026", "Петренко Марія", "09:15", "17:15", "8 год 0 хв"],
    ]
    with patch.object(sheets, '_get_worksheet', return_value=mock_ws):
        result = sheets.get_attendance_by_name_and_month("Іваненко Олена", "Серпень 2026")
    assert result == []


def test_returns_empty_when_sheet_not_found():
    with patch.object(sheets, '_get_worksheet', return_value=None):
        result = sheets.get_attendance_by_name_and_month("Іваненко Олена", "Серпень 2026")
    assert result == []


def test_returns_all_records_for_worker_across_multiple_days():
    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["Дата", "Ім'я Прізвище", "Прийшла", "Пішла", "Відпрацьовано"],
        ["01.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"],
        ["02.08.2026", "Іваненко Олена", "09:00", "18:00", "9 год 0 хв"],
        ["02.08.2026", "Петренко Марія", "09:00", "17:00", "8 год 0 хв"],
    ]
    with patch.object(sheets, '_get_worksheet', return_value=mock_ws):
        result = sheets.get_attendance_by_name_and_month("Іваненко Олена", "Серпень 2026")
    assert len(result) == 2
    assert result[0]["Дата"] == "01.08.2026"
    assert result[1]["Дата"] == "02.08.2026"
