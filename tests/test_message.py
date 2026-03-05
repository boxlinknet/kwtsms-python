"""Tests for clean_message()."""
from kwtsms import clean_message


def test_strips_emoji():
    result = clean_message("Hello 🎉")
    assert "🎉" not in result
    assert "Hello" in result


def test_converts_arabic_indic_digits_to_latin():
    # ١٢٣ = 123 in Arabic-Indic digits
    assert clean_message("Order ١٢٣") == "Order 123"


def test_strips_zero_width_space():
    assert clean_message("Hello\u200BWorld") == "HelloWorld"


def test_strips_html_tags():
    assert clean_message("Hello<b>World</b>") == "HelloWorld"


def test_preserves_arabic_text():
    # Arabic letters must NOT be stripped
    assert clean_message("مرحبا") == "مرحبا"


def test_preserves_newlines():
    assert clean_message("Line1\nLine2") == "Line1\nLine2"


def test_strips_bom():
    assert clean_message("\uFEFFHello") == "Hello"


def test_strips_soft_hyphen():
    assert clean_message("soft\u00ADhyphen") == "softhyphen"


def test_clean_message_passthrough_for_plain_text():
    """A plain ASCII message must pass through clean_message unchanged."""
    msg = "Your OTP is 123456"
    assert clean_message(msg) == msg


def test_converts_extended_arabic_indic_digits_in_message():
    # ۱۲۳ = 123 in Extended Arabic-Indic (Persian)
    assert clean_message("Order ۱۲۳") == "Order 123"


# ── Extended emoji ranges ──────────────────────────────────────────────────────

def test_strips_country_flag_regional_indicators():
    # 🇰🇼 = regional indicator K (U+1F1F0) + W (U+1F1FC)
    result = clean_message("Hello 🇰🇼")
    assert "\U0001F1F0" not in result
    assert "\U0001F1FC" not in result
    assert "Hello" in result


def test_strips_keycap_emoji():
    # 1️⃣ = "1" + U+FE0F (variation selector) + U+20E3 (combining enclosing keycap)
    result = clean_message("Press 1\uFE0F\u20E3 to confirm")
    assert "\u20E3" not in result
    assert "Press" in result
    assert "to confirm" in result


def test_strips_mahjong_tile():
    # U+1F004 = Mahjong Tile Red Dragon (outside the previously covered ranges)
    result = clean_message("Game \U0001F004 over")
    assert "\U0001F004" not in result
    assert "Game" in result
    assert "over" in result


def test_strips_tags_block_character():
    # U+E0067 = tag letter g (used in subdivision flags like 🏴󠁧󠁢󠁥󠁮󠁧󠁿)
    result = clean_message("Flag \U000E0067 text")
    assert "\U000E0067" not in result
    assert "Flag" in result
    assert "text" in result


def test_emoji_only_message_becomes_empty():
    """A message consisting entirely of emoji should become an empty string."""
    assert clean_message("🎉🎊🚀") == ""


def test_emoji_only_with_spaces_cleans_to_spaces():
    """Spaces around emoji are preserved; only the emoji chars are stripped."""
    result = clean_message(" 🎉 ")
    assert "🎉" not in result
    assert result.strip() == ""
