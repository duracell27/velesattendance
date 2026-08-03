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


def test_get_available_months_returns_empty_when_no_month_sheets():
    mock_ws = MagicMock(); mock_ws.title = "users"
    with patch.object(sheets, '_get_spreadsheet') as mock_sp:
        mock_sp.return_value.worksheets.return_value = [mock_ws]
        result = sheets.get_available_months()
    assert result == []


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
         patch.object(sheets, 'update_monthly_summary') as mock_update, \
         patch.object(sheets, 'calculate_hours_worked', return_value="8 год 0 хв") as mock_hours:
        result = sheets.add_record("03.08.2026", "Іваненко Олена", "09:00", "17:00")
    assert result is True
    mock_ws.append_rows.assert_called_once_with(
        [["03.08.2026", "Іваненко Олена", "09:00", "17:00", "8 год 0 хв"]],
        table_range="A1",
    )
    mock_update.assert_called_once()
    mock_hours.assert_called_once_with("09:00", "17:00")


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
