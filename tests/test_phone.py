"""Tests for normalize_phone(), validate_phone_input(), find_country_code(), validate_phone_format()."""
from kwtsms import normalize_phone, validate_phone_input, find_country_code, validate_phone_format


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
    ok, error, _ = validate_phone_input("8887654")  # exactly 7 digits, no country code match
    assert ok is True
    assert error is None


def test_too_long_number():
    ok, error, _ = validate_phone_input("1234567890123456")  # 16 digits
    assert ok is False
    assert "too long" in error.lower()


def test_maximum_valid_length():
    ok, error, _ = validate_phone_input("888456789012345")  # exactly 15 digits, no country code match
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


# ── Trunk prefix stripping ───────────────────────────────────────────────────

def test_saudi_trunk_prefix_stripped():
    """9660559123456 → 966559123456 (leading 0 after country code stripped)."""
    assert normalize_phone("9660559123456") == "966559123456"


def test_saudi_with_plus_and_trunk():
    assert normalize_phone("+9660551234567") == "966551234567"


def test_saudi_with_00_and_trunk():
    assert normalize_phone("009660551234567") == "966551234567"


def test_uae_trunk_prefix_stripped():
    """97105xxxxxxx → 9715xxxxxxx."""
    assert normalize_phone("971050123456") == "97150123456"


def test_egypt_trunk_prefix_stripped():
    """20010xxxxxxx → 2010xxxxxxx."""
    assert normalize_phone("200101234567") == "20101234567"


def test_kuwait_no_trunk_prefix():
    """Kuwait numbers don't have trunk prefix, should be unchanged."""
    assert normalize_phone("96598765432") == "96598765432"


def test_validate_saudi_with_trunk():
    """Full validation flow: Saudi with trunk prefix should normalize and validate."""
    ok, error, normalized = validate_phone_input("+9660559123456")
    assert ok is True
    assert normalized == "966559123456"


# ── find_country_code() ──────────────────────────────────────────────────────

def test_find_country_code_kuwait():
    assert find_country_code("96598765432") == "965"


def test_find_country_code_usa():
    assert find_country_code("12125551234") == "1"


def test_find_country_code_egypt():
    assert find_country_code("201012345678") == "20"


def test_find_country_code_czech():
    assert find_country_code("420612345678") == "420"


def test_find_country_code_unknown():
    assert find_country_code("8887654321") is None


def test_find_country_code_empty():
    assert find_country_code("") is None


# ── validate_phone_format() ──────────────────────────────────────────────────

def test_format_valid_kuwait():
    ok, error = validate_phone_format("96598765432")
    assert ok is True
    assert error is None


def test_format_invalid_kuwait_prefix():
    """Kuwait mobile must start with 4, 5, 6, or 9 after +965."""
    ok, error = validate_phone_format("96512345678")
    assert ok is False
    assert "Kuwait" in error
    assert "4, 5, 6, 9" in error


def test_format_invalid_kuwait_length():
    """Kuwait local part must be 8 digits."""
    ok, error = validate_phone_format("9659876543")  # only 7 local digits
    assert ok is False
    assert "Kuwait" in error
    assert "8 digits" in error


def test_format_valid_saudi():
    ok, error = validate_phone_format("966551234567")
    assert ok is True


def test_format_invalid_saudi_prefix():
    """Saudi mobile must start with 5 after +966."""
    ok, error = validate_phone_format("966311234567")
    assert ok is False
    assert "Saudi" in error


def test_format_valid_usa():
    ok, error = validate_phone_format("12125551234")
    assert ok is True


def test_format_invalid_usa_length():
    ok, error = validate_phone_format("121255512")  # 8 local digits, needs 10
    assert ok is False
    assert "USA" in error


def test_format_unknown_country_passes():
    """Numbers with no matching country rule pass through."""
    ok, error = validate_phone_format("8887654321")
    assert ok is True


def test_format_valid_uk():
    ok, error = validate_phone_format("447911123456")
    assert ok is True


def test_format_valid_india():
    ok, error = validate_phone_format("919876543210")
    assert ok is True


def test_format_invalid_india_prefix():
    """India mobile must start with 6, 7, 8, or 9 after +91."""
    ok, error = validate_phone_format("911234567890")
    assert ok is False
    assert "India" in error
