from keyboards.main import get_main_keyboard


def _all_texts(kb):
    return [btn.text for row in kb.keyboard for btn in row]


def test_admin_keyboard_has_edit_schedule_button():
    kb = get_main_keyboard(is_admin=True)
    assert "📝 Редагувати графік" in _all_texts(kb)


def test_non_admin_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard(is_admin=False)
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_default_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard()
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_admin_checked_in_keyboard_has_all_buttons():
    kb = get_main_keyboard(checked_in=True, is_admin=True)
    texts = _all_texts(kb)
    assert "🚪 Пішла з роботи" in texts
    assert "📊 Моя відвідуваність" in texts
    assert "📝 Редагувати графік" in texts
    assert "✅ Прийшла на роботу" not in texts


def test_admin_checked_out_keyboard_has_edit_button():
    kb = get_main_keyboard(checked_out=True, is_admin=True)
    texts = _all_texts(kb)
    assert "📊 Моя відвідуваність" in texts
    assert "📝 Редагувати графік" in texts
