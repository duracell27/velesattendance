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
