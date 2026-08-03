from keyboards.schedule_edit import (
    action_keyboard, month_keyboard, worker_keyboard,
    day_keyboard, field_keyboard, confirm_delete_keyboard,
)


def _all_callbacks(kb):
    return [btn.callback_data for row in kb.inline_keyboard for btn in row]


def _all_texts(kb):
    return [btn.text for row in kb.inline_keyboard for btn in row]


def test_action_keyboard_has_three_actions_and_cancel():
    kb = action_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:action:add" in cbs
    assert "se:action:edit" in cbs
    assert "se:action:delete" in cbs
    assert "se:cancel" in cbs


def test_month_keyboard_has_cancel_and_all_months():
    months = ["Серпень 2026", "Липень 2026"]
    kb = month_keyboard(months)
    cbs = _all_callbacks(kb)
    assert "se:month:Серпень 2026" in cbs
    assert "se:month:Липень 2026" in cbs
    assert "se:cancel" in cbs


def test_worker_keyboard_has_all_workers_and_cancel():
    workers = [
        {"Ім'я Прізвище": "Іваненко Олена"},
        {"Ім'я Прізвище": "Петренко Марія"},
    ]
    kb = worker_keyboard(workers)
    cbs = _all_callbacks(kb)
    texts = _all_texts(kb)
    # callback data uses index, not name
    assert "se:worker:0" in cbs
    assert "se:worker:1" in cbs
    # button text still shows names
    assert "Іваненко Олена" in texts
    assert "Петренко Марія" in texts
    assert "se:cancel" in cbs


def test_day_keyboard_august_has_31_days():
    kb = day_keyboard(2026, 8)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 31
    assert "se:day:1" in day_cbs
    assert "se:day:31" in day_cbs


def test_day_keyboard_february_non_leap_has_28_days():
    kb = day_keyboard(2025, 2)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 28


def test_day_keyboard_february_leap_has_29_days():
    kb = day_keyboard(2024, 2)
    day_cbs = [c for c in _all_callbacks(kb) if c.startswith("se:day:")]
    assert len(day_cbs) == 29


def test_day_keyboard_rows_have_max_5_buttons_excluding_cancel():
    kb = day_keyboard(2026, 8)
    # all rows except last (cancel row) should have ≤ 5 buttons
    for row in kb.inline_keyboard[:-1]:
        assert len(row) <= 5


def test_field_keyboard_has_pryyshla_and_pishla():
    kb = field_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:field:Прийшла" in cbs
    assert "se:field:Пішла" in cbs
    assert "se:cancel" in cbs


def test_confirm_delete_keyboard_has_confirm_and_cancel():
    kb = confirm_delete_keyboard()
    cbs = _all_callbacks(kb)
    assert "se:confirm:yes" in cbs
    assert "se:cancel" in cbs
