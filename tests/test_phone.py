"""Tests for normalize_phone() and validate_phone_input()."""
from kwtsms import normalize_phone, validate_phone_input


def test_strips_plus_prefix():
    assert normalize_phone("+96598765432") == "96598765432"


def test_strips_double_zero_prefix():
    assert normalize_phone("0096598765432") == "96598765432"


def test_strips_spaces():
    assert normalize_phone("965 9876 5432") == "96598765432"


def test_strips_dashes():
    assert normalize_phone("965-9876-5432") == "96598765432"


def test_converts_arabic_indic_digits():
    # ٩٦٥٩٨٧٦٥٤٣٢ = 96598765432 in Arabic-Indic
    assert normalize_phone("٩٦٥٩٨٧٦٥٤٣٢") == "96598765432"


def test_strips_leading_zeros_after_00_prefix():
    assert normalize_phone("00 965 9876-5432") == "96598765432"


def test_empty_string():
    assert normalize_phone("") == ""


def test_digits_only_unchanged():
    assert normalize_phone("96598765432") == "96598765432"


# ── validate_phone_input() ────────────────────────────────────────────────────

def test_valid_number_returns_true():
    ok, error, normalized = validate_phone_input("+96598765432")
    assert ok is True
    assert error is None
    assert normalized == "96598765432"


def test_valid_number_with_spaces():
    ok, error, normalized = validate_phone_input("965 9876 5432")
    assert ok is True
    assert normalized == "96598765432"


def test_empty_string_returns_required_error():
    ok, error, _ = validate_phone_input("")
    assert ok is False
    assert "required" in error.lower()


def test_blank_whitespace_returns_required_error():
    ok, error, _ = validate_phone_input("   ")
    assert ok is False
    assert "required" in error.lower()


def test_email_address_returns_clear_error():
    ok, error, _ = validate_phone_input("user@gmail.com")
    assert ok is False
    assert "email" in error.lower()


def test_email_with_plus_returns_clear_error():
    ok, error, _ = validate_phone_input("my+name@domain.com")
    assert ok is False
    assert "email" in error.lower()


def test_letters_only_returns_no_digits_error():
    ok, error, _ = validate_phone_input("abc")
    assert ok is False
    assert "no digits" in error.lower()


def test_dashes_only_returns_no_digits_error():
    ok, error, _ = validate_phone_input("---")
    assert ok is False
    assert "no digits" in error.lower()


def test_mixed_letters_and_digits_too_short():
    # "abc123" → normalizes to "123" → too short
    ok, error, _ = validate_phone_input("abc123")
    assert ok is False
    assert "too short" in error.lower()


def test_too_short_number():
    ok, error, _ = validate_phone_input("123456")  # 6 digits
    assert ok is False
    assert "too short" in error.lower()


def test_minimum_valid_length():
    ok, error, _ = validate_phone_input("1234567")  # exactly 7 digits
    assert ok is True
    assert error is None


def test_too_long_number():
    ok, error, _ = validate_phone_input("1234567890123456")  # 16 digits
    assert ok is False
    assert "too long" in error.lower()


def test_maximum_valid_length():
    ok, error, _ = validate_phone_input("123456789012345")  # exactly 15 digits
    assert ok is True
    assert error is None


def test_arabic_digits_valid_number():
    # ٩٦٥٩٨٧٦٥٤٣٢ = 96598765432
    ok, error, normalized = validate_phone_input("٩٦٥٩٨٧٦٥٤٣٢")
    assert ok is True
    assert normalized == "96598765432"


def test_converts_extended_arabic_indic_digits():
    # ۹۶۵۹۸۷۶۵۴۳۲ = 96598765432 in Extended Arabic-Indic (Persian)
    assert normalize_phone("۹۶۵۹۸۷۶۵۴۳۲") == "96598765432"


def test_converts_mixed_arabic_and_persian_digits():
    # Mix of Arabic-Indic (٩٦٥) and Extended Arabic-Indic (۹۸۷۶۵۴۳۲)
    assert normalize_phone("٩٦٥۹۸۷۶۵۴۳۲") == "96598765432"
