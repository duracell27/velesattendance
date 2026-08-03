from keyboards.admin_report import ar_month_keyboard, ar_worker_keyboard


def _all_callbacks(kb):
    return [btn.callback_data for row in kb.inline_keyboard for btn in row]


def _all_texts(kb):
    return [btn.text for row in kb.inline_keyboard for btn in row]


def test_ar_month_keyboard_has_months_and_cancel():
    months = ["Серпень 2026", "Липень 2026"]
    kb = ar_month_keyboard(months)
    cbs = _all_callbacks(kb)
    assert "ar:month:Серпень 2026" in cbs
    assert "ar:month:Липень 2026" in cbs
    assert "ar:cancel" in cbs


def test_ar_month_keyboard_empty_list_still_has_cancel():
    kb = ar_month_keyboard([])
    assert "ar:cancel" in _all_callbacks(kb)


def test_ar_worker_keyboard_uses_index_callbacks():
    workers = [{"Ім'я Прізвище": "Іваненко Олена"}, {"Ім'я Прізвище": "Петренко Марія"}]
    kb = ar_worker_keyboard(workers)
    cbs = _all_callbacks(kb)
    assert "ar:worker:0" in cbs
    assert "ar:worker:1" in cbs
    assert "ar:cancel" in cbs


def test_ar_worker_keyboard_shows_names_as_button_text():
    workers = [{"Ім'я Прізвище": "Іваненко Олена"}, {"Ім'я Прізвище": "Петренко Марія"}]
    kb = ar_worker_keyboard(workers)
    texts = _all_texts(kb)
    assert "Іваненко Олена" in texts
    assert "Петренко Марія" in texts


def test_ar_worker_keyboard_max_two_per_row():
    workers = [
        {"Ім'я Прізвище": "Іваненко Олена"},
        {"Ім'я Прізвище": "Петренко Марія"},
        {"Ім'я Прізвище": "Коваленко Ніна"},
    ]
    kb = ar_worker_keyboard(workers)
    worker_rows = [
        row for row in kb.inline_keyboard
        if any(b.callback_data.startswith("ar:worker:") for b in row)
    ]
    assert all(len(row) <= 2 for row in worker_rows)
    assert len(worker_rows) == 2  # 3 workers → 2 rows (2+1)
