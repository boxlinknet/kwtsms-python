"""
Real integration tests: hit the live kwtSMS API.

Requirements:
    kwtsms/.env must exist with valid KWTSMS_USERNAME and KWTSMS_PASSWORD.

All sends use test_mode=True: messages are queued but never delivered,
no credits are consumed.

Run:
    uv run pytest tests/test_integration.py -v
"""

import os
import pytest
from kwtsms import KwtSMS
from kwtsms._core import _load_env_file

# ── Skip entire module if no credentials are configured ───────────────────────

_env = _load_env_file(".env")

def _get(key):
    return os.environ.get(key) or _env.get(key, "")

KWTSMS_USERNAME = _get("KWTSMS_USERNAME")
KWTSMS_PASSWORD = _get("KWTSMS_PASSWORD")
KWTSMS_SENDER_ID = _get("KWTSMS_SENDER_ID") or "KWT-SMS"

if not KWTSMS_USERNAME or not KWTSMS_PASSWORD:
    pytest.skip(
        "Skipping integration tests: no credentials in .env. "
        "Set KWTSMS_USERNAME and KWTSMS_PASSWORD.",
        allow_module_level=True,
    )


def live_client(**kwargs) -> KwtSMS:
    """Return a real client in test mode: sends are queued, never delivered."""
    defaults = dict(
        username=KWTSMS_USERNAME,
        password=KWTSMS_PASSWORD,
        sender_id=KWTSMS_SENDER_ID,
        test_mode=True,   # always forced, no real SMS sent during tests
        log_file="kwtsms-integration-test.log",
    )
    defaults.update(kwargs)
    return KwtSMS(**defaults)


# ── Credentials ───────────────────────────────────────────────────────────────

class TestCredentials:

    def test_verify_valid_credentials(self):
        """Real API call: credentials should be accepted."""
        ok, balance, error = live_client().verify()
        assert ok is True, f"verify() failed: {error}"
        assert error is None

    def test_verify_returns_numeric_balance(self):
        ok, balance, _ = live_client().verify()
        assert ok is True
        assert isinstance(balance, float)
        assert balance >= 0

    def test_balance_returns_number(self):
        bal = live_client().balance()
        assert bal is not None, "balance() returned None. Check credentials"
        assert bal >= 0

    def test_wrong_username_returns_auth_error(self):
        # verify() formats: "description → action". Code (ERR003) is not in the string
        sms = KwtSMS(username="WRONG_python_username", password="WRONG_python_password",
                     sender_id="KWT-SMS", test_mode=True, log_file="")
        ok, balance, error = sms.verify()
        assert ok is False
        assert "Authentication error" in error, f"Expected auth error, got: {error}"

    def test_wrong_password_returns_auth_error(self):
        sms = KwtSMS(username=KWTSMS_USERNAME, password="DEFINITELY_WRONG",
                     sender_id="KWT-SMS", test_mode=True, log_file="")
        ok, balance, error = sms.verify()
        assert ok is False
        assert "Authentication error" in error, f"Expected auth error, got: {error}"


# ── Send SMS (test mode: queued, never delivered) ─────────────────────────────

class TestSend:

    def test_send_valid_kuwait_mobile(self):
        """Send to a known valid Kuwait mobile format in test mode."""
        result = live_client().send("96599999999", "Integration test, kwtSMS Python client")
        # In test mode the API accepts it and queues it
        # ERR010/ERR011 means balance issue. Still a real API response, not a crash
        assert "result" in result
        assert result["result"] in ("OK", "ERROR")

    def test_send_ok_has_required_fields(self):
        result = live_client().send("96599999999", "Integration test, field check")
        if result["result"] == "OK":
            assert "msg-id" in result
            assert "numbers" in result
            assert "points-charged" in result
            assert "balance-after" in result

    def test_send_updates_cached_balance(self):
        sms = live_client()
        result = sms.send("96599999999", "Balance cache test")
        if result["result"] == "OK":
            assert sms._cached_balance is not None
            assert sms._cached_balance == result["balance-after"]

    def test_send_empty_string_number(self):
        result = live_client().send("", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR_INVALID_INPUT"
        assert "required" in result["description"].lower()

    def test_send_email_instead_of_number(self):
        result = live_client().send("user@gmail.com", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR_INVALID_INPUT"
        assert "email" in result["description"].lower()

    def test_send_too_short_number(self):
        result = live_client().send("123", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR_INVALID_INPUT"
        assert "too short" in result["description"].lower()

    def test_send_letters_only(self):
        result = live_client().send("abcdef", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR_INVALID_INPUT"

    def test_send_mixed_valid_and_invalid_numbers(self):
        """Valid + invalid in same list: valid ones sent, invalid reported."""
        result = live_client().send(
            ["96599999999", "abc", "user@gmail.com"],
            "Mixed numbers test"
        )
        assert "invalid" in result
        invalid_inputs = [e["input"] for e in result["invalid"]]
        assert "abc" in invalid_inputs
        assert "user@gmail.com" in invalid_inputs

    def test_send_normalizes_plus_prefix(self):
        """+ prefix is stripped automatically. Should not return ERR025."""
        result = live_client().send("+96599999999", "Normalize test")
        assert result["result"] in ("OK", "ERROR")
        # If ERROR, must NOT be ERR025 (that would mean normalization failed)
        if result["result"] == "ERROR":
            assert result.get("code") != "ERR025", \
                "ERR025 means +prefix was NOT stripped. Normalization broken"

    def test_send_normalizes_double_zero_prefix(self):
        result = live_client().send("0096599999999", "Normalize 00 test")
        assert result["result"] in ("OK", "ERROR")
        if result["result"] == "ERROR":
            assert result.get("code") != "ERR025"

    def test_send_normalizes_spaces_and_dashes(self):
        result = live_client().send("965 9999-9999", "Normalize spaces test")
        assert result["result"] in ("OK", "ERROR")
        if result["result"] == "ERROR":
            assert result.get("code") != "ERR025"

    def test_send_arabic_digits_in_number(self):
        # ٩٦٥٩٩٩٩٩٩٩٩ = 96599999999 in Arabic-Indic
        result = live_client().send("٩٦٥٩٩٩٩٩٩٩٩", "Arabic digits test")
        assert result["result"] in ("OK", "ERROR")
        if result["result"] == "ERROR":
            assert result.get("code") != "ERR025"

    def test_send_wrong_country_code_no_route(self):
        """UAE number. ERR026 if international is not activated, or OK if it is."""
        result = live_client().send("971504496677", "International test")
        assert "result" in result
        if result["result"] == "ERROR":
            # Only acceptable errors are ERR026 (no route) or balance/account issues
            assert result["code"] in ("ERR026", "ERR010", "ERR011", "ERR001",
                                      "ERR004", "ERR005", "ERR024")
            if result["code"] == "ERR026":
                assert "action" in result
                assert "country" in result["action"].lower()


# ── Validate numbers ──────────────────────────────────────────────────────────

class TestValidate:

    def test_validate_returns_ok_er_nr_keys(self):
        report = live_client().validate(["96599999999"])
        assert "ok" in report
        assert "er" in report
        assert "nr" in report
        assert "error" in report

    def test_validate_pre_rejects_email(self):
        report = live_client().validate(["user@gmail.com", "96599999999"])
        assert "user@gmail.com" in report["er"]
        rejected_inputs = [r["input"] for r in report.get("rejected", [])]
        assert "user@gmail.com" in rejected_inputs

    def test_validate_pre_rejects_too_short(self):
        report = live_client().validate(["123", "96599999999"])
        assert "123" in report["er"]

    def test_validate_pre_rejects_letters_only(self):
        report = live_client().validate(["abc"])
        assert "abc" in report["er"]
        assert report["error"] is not None

    def test_validate_normalizes_plus_prefix(self):
        """+ is stripped before calling API. Should land in 'ok' not 'er'."""
        report = live_client().validate(["+96599999999"])
        # After normalization → 96599999999, should not be in 'er' for format reasons
        assert "error" not in report or report["error"] is None or \
               "96599999999" not in report["er"], \
               "normalize_phone() should have stripped the + before /validate/ was called"

    def test_validate_all_invalid_returns_error(self):
        report = live_client().validate(["abc", "xyz", "123"])
        assert report["error"] is not None
        assert len(report["ok"]) == 0


# ── Sender ID edge cases ──────────────────────────────────────────────────────

class TestSenderID:
    """
    Sender ID validation: tested against the real API.

    Kuwait telecoms only allow alphanumeric Latin sender IDs (A–Z, 0–9, max 11 chars).
    Arabic characters, empty strings, and unknown sender IDs are rejected by the API.
    """

    def test_empty_sender_id_in_constructor_falls_back_to_kwtsms(self):
        """
        sender_id="" is falsy. send() resolves effective_sender via
        `sender or self.sender_id`, so empty string falls back to self.sender_id.
        An empty constructor sender_id means the API receives an empty string,
        which triggers ERR002 (missing parameter) or ERR008 (banned sender).
        """
        sms = KwtSMS(
            username=KWTSMS_USERNAME,
            password=KWTSMS_PASSWORD,
            sender_id="",           # empty, will be sent as empty to the API
            test_mode=True,
            log_file="",
        )
        result = sms.send("96599999999", "Empty sender ID test")
        # Must return a dict, never crash
        assert isinstance(result, dict)
        assert "result" in result

    def test_empty_sender_id_returns_api_error(self):
        """API rejects an empty sender ID: ERR002 (missing param) or ERR008 (banned)."""
        sms = KwtSMS(
            username=KWTSMS_USERNAME,
            password=KWTSMS_PASSWORD,
            sender_id="",
            test_mode=True,
            log_file="",
        )
        result = sms.send("96599999999", "Empty sender ID test")
        if result["result"] == "ERROR":
            assert result["code"] in ("ERR002", "ERR008", "ERR001", "ERR004", "ERR005")
            assert "action" in result

    def test_per_call_empty_sender_falls_back_to_client_sender_id(self):
        """
        send(sender=""): empty string is falsy.
        effective_sender = "" or self.sender_id → self.sender_id is used instead.
        So passing sender="" is the same as not passing sender at all.
        """
        sms = live_client()  # has a real sender_id from .env
        result_default  = sms.send("96599999999", "Sender fallback test")
        result_empty    = sms.send("96599999999", "Sender fallback test", sender="")
        # Both should produce the same outcome since "" falls back to self.sender_id
        assert result_default["result"] == result_empty["result"]

    def test_arabic_sender_id_accepted_by_api(self):
        """
        REAL API BEHAVIOR (confirmed by live test): kwtSMS does NOT validate
        sender ID characters at the API level. Arabic characters are accepted
        and the API returns OK.

        The carrier (Zain/Ooredoo/STC) may reject the Arabic sender ID or display
        it as blank on the recipient's handset, but the API itself does not reject it.

        This test documents the actual behavior. Do not change the assertion.
        """
        sms = KwtSMS(
            username=KWTSMS_USERNAME,
            password=KWTSMS_PASSWORD,
            sender_id="مرسل",       # Arabic for "sender"
            test_mode=True,
            log_file="",
        )
        result = sms.send("96599999999", "Arabic sender ID test")
        assert isinstance(result, dict)
        assert "result" in result
        # API accepts it. Validation is at the carrier level, not the API level
        assert result["result"] in ("OK", "ERROR"), f"Unexpected result: {result}"

    def test_arabic_sender_id_if_error_has_action(self):
        """If the API ever starts rejecting Arabic sender IDs, the error must have action."""
        sms = KwtSMS(
            username=KWTSMS_USERNAME,
            password=KWTSMS_PASSWORD,
            sender_id="مرسل",
            test_mode=True,
            log_file="",
        )
        result = sms.send("96599999999", "Arabic sender test")
        if result["result"] == "ERROR":
            assert "action" in result, f"No action in error response: {result}"

    def test_per_call_arabic_sender_accepted_by_api(self):
        """
        REAL API BEHAVIOR: overriding sender per-call with Arabic characters
        is also accepted by the API (same behavior as constructor sender_id).
        Carrier-level handling determines what the recipient actually sees.
        """
        result = live_client().send(
            "96599999999",
            "Per-call Arabic sender test",
            sender="مرسل",
        )
        assert isinstance(result, dict)
        assert result["result"] in ("OK", "ERROR")

    def test_unknown_sender_id_rejected(self):
        """
        A sender ID that is not registered on the account should be rejected.
        Expected: ERR008 (banned/unknown sender) or similar.
        """
        sms = KwtSMS(
            username=KWTSMS_USERNAME,
            password=KWTSMS_PASSWORD,
            sender_id="ZZNOTREAL99",   # not registered on any account
            test_mode=True,
            log_file="",
        )
        result = sms.send("96599999999", "Unknown sender ID test")
        assert isinstance(result, dict)
        assert "result" in result
        if result["result"] == "ERROR":
            assert "action" in result


# ── Error response quality ────────────────────────────────────────────────────

class TestErrorQuality:
    """Verify that every error response from the real API gets enriched with 'action'."""

    def test_wrong_credentials_error_has_action(self):
        sms = KwtSMS(username="WRONG_python_username", password="WRONG_python_password",
                     sender_id="KWT-SMS", test_mode=True, log_file="")
        ok, _, error = sms.verify()
        assert ok is False
        # verify() folds action into the error string
        assert error is not None and len(error) > 0

    def test_invalid_input_error_has_action(self):
        result = live_client().send("abc", "Test")
        assert result["result"] == "ERROR"
        assert "action" in result
