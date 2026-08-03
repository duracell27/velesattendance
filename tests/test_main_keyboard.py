from keyboards.main import get_main_keyboard


def _all_texts(kb):
    return [btn.text for row in kb.keyboard for btn in row]


def test_admin_keyboard_has_edit_schedule_button():
    kb = get_main_keyboard(is_admin=True)
    assert "📝 Редагувати графік" in _all_texts(kb)


def test_admin_keyboard_has_zvit_button():
    kb = get_main_keyboard(is_admin=True)
    assert "📊 Звіт відвідуваності" in _all_texts(kb)


def test_admin_keyboard_always_shows_fixed_layout():
    for checked_in, checked_out in [(False, False), (True, False), (False, True)]:
        kb = get_main_keyboard(checked_in=checked_in, checked_out=checked_out, is_admin=True)
        texts = _all_texts(kb)
        assert "📊 Звіт відвідуваності" in texts
        assert "📝 Редагувати графік" in texts
        assert "✅ Прийшла на роботу" not in texts
        assert "🚪 Пішла з роботи" not in texts
        assert "📊 Моя відвідуваність" not in texts


def test_non_admin_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard(is_admin=False)
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_non_admin_keyboard_has_moia_vidviduvalnist():
    kb = get_main_keyboard(is_admin=False)
    assert "📊 Моя відвідуваність" in _all_texts(kb)


def test_default_keyboard_has_no_edit_schedule_button():
    kb = get_main_keyboard()
    assert "📝 Редагувати графік" not in _all_texts(kb)


def test_non_admin_checked_in_has_correct_buttons():
    kb = get_main_keyboard(checked_in=True, is_admin=False)
    texts = _all_texts(kb)
    assert "🚪 Пішла з роботи" in texts
    assert "📊 Моя відвідуваність" in texts
    assert "✅ Прийшла на роботу" not in texts


def test_non_admin_checked_out_has_only_attendance():
    kb = get_main_keyboard(checked_out=True, is_admin=False)
    texts = _all_texts(kb)
    assert "📊 Моя відвідуваність" in texts
    assert "🚪 Пішла з роботи" not in texts
