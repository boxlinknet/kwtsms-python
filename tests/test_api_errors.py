"""
Tests for API error handling and meaningful error messages.

All tests mock _request(): no real network calls are made.
Each test simulates a specific API error response and verifies that:
  1. The result never crashes / always returns a dict or tuple
  2. The error code is preserved
  3. An 'action' field is present with developer-friendly guidance
  4. The error message is human-readable
"""

from unittest.mock import patch

import pytest

from kwtsms import KwtSMS


def _client(**kwargs) -> KwtSMS:
    """Return a test client with dummy credentials. log_file="" disables logging."""
    defaults = dict(username="python_username", password="python_password", sender_id="TEST", log_file="")
    defaults.update(kwargs)
    return KwtSMS(**defaults)


# ── Wrong credentials (ERR003) ────────────────────────────────────────────────

class TestWrongCredentials:
    """ERR003: wrong API username or password."""

    ERR003_RESPONSE = {
        "result":      "ERROR",
        "code":        "ERR003",
        "description": "Authentication error, username or password are not correct.",
    }

    def test_verify_returns_false_not_exception(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            ok, balance, error = _client().verify()
        assert ok is False
        assert balance is None

    def test_verify_error_contains_api_description(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            _, _, error = _client().verify()
        assert "Authentication error" in error

    def test_verify_error_contains_action_guidance(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            _, _, error = _client().verify()
        # action should tell the developer what to check
        assert "KWTSMS_USERNAME" in error or "API credentials" in error

    def test_send_with_wrong_credentials_returns_error_dict(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR003"

    def test_send_with_wrong_credentials_has_action(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            result = _client().send("96598765432", "Test")
        assert "action" in result
        assert len(result["action"]) > 0

    def test_balance_returns_none_not_exception(self):
        with patch("kwtsms._core._request", return_value=self.ERR003_RESPONSE):
            bal = _client().balance()
        assert bal is None


# ── Country not allowed (ERR026) ──────────────────────────────────────────────

class TestCountryNotAllowed:
    """ERR026: no route for the destination country prefix."""

    ERR026_RESPONSE = {
        "result":      "ERROR",
        "code":        "ERR026",
        "description": "No route for this country prefix.",
    }

    def test_send_to_disallowed_country_returns_error(self):
        # UAE number. International sending not activated by default
        with patch("kwtsms._core._request", return_value=self.ERR026_RESPONSE):
            result = _client().send("971504496677", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR026"

    def test_send_to_disallowed_country_has_action(self):
        with patch("kwtsms._core._request", return_value=self.ERR026_RESPONSE):
            result = _client().send("971504496677", "Test")
        assert "action" in result
        assert "kwtSMS support" in result["action"]

    def test_action_mentions_country_activation(self):
        with patch("kwtsms._core._request", return_value=self.ERR026_RESPONSE):
            result = _client().send("971504496677", "Test")
        assert "country" in result["action"].lower()

    def test_does_not_raise_exception(self):
        with patch("kwtsms._core._request", return_value=self.ERR026_RESPONSE):
            result = _client().send("971504496677", "Test")
        assert isinstance(result, dict)


# ── Invalid Kuwait number (ERR025) ────────────────────────────────────────────

class TestInvalidKuwaitNumber:
    """
    96512345678: passes local length/format validation (11 digits, no non-digits)
    but is rejected by the kwtSMS API because the local portion (12345678) does
    not match any valid Kuwait mobile or landline prefix.

    The API returns ERR025 (invalid number: non-digit chars or unrecognised format).
    """

    ERR025_RESPONSE = {
        "result":      "ERROR",
        "code":        "ERR025",
        "description": "Invalid phone number.",
    }

    def test_invalid_kuwait_number_passes_local_validation(self):
        """96512345678 has 11 digits so our local validator accepts it.
        The API is the one that rejects it. We must surface that rejection clearly."""
        from kwtsms import validate_phone_input
        ok, error, normalized = validate_phone_input("96512345678")
        assert ok is True           # local check passes: length is fine
        assert normalized == "96512345678"

    def test_api_rejection_surfaced_as_error_dict(self):
        with patch("kwtsms._core._request", return_value=self.ERR025_RESPONSE):
            result = _client().send("96512345678", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR025"

    def test_api_rejection_has_action(self):
        with patch("kwtsms._core._request", return_value=self.ERR025_RESPONSE):
            result = _client().send("96512345678", "Test")
        assert "action" in result
        assert "country code" in result["action"] or "international format" in result["action"]

    def test_does_not_raise_exception(self):
        with patch("kwtsms._core._request", return_value=self.ERR025_RESPONSE):
            result = _client().send("96512345678", "Test")
        assert isinstance(result, dict)


# ── Zero balance (ERR010) ─────────────────────────────────────────────────────

class TestZeroBalance:
    """ERR010: account has no credits."""

    def test_send_with_zero_balance_returns_error(self):
        resp = {"result": "ERROR", "code": "ERR010", "description": "Zero balance."}
        with patch("kwtsms._core._request", return_value=resp):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR010"
        assert "action" in result
        assert "kwtsms.com" in result["action"]


# ── IP not whitelisted (ERR024) ───────────────────────────────────────────────

class TestIPNotWhitelisted:
    """ERR024: IP lockdown is enabled and this IP is not in the whitelist."""

    def test_ip_not_whitelisted_has_clear_action(self):
        resp = {"result": "ERROR", "code": "ERR024", "description": "IP not allowed."}
        with patch("kwtsms._core._request", return_value=resp):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert "action" in result
        assert "IP" in result["action"] or "whitelist" in result["action"].lower()


# ── Rate limit: send too fast (ERR028) ────────────────────────────────────────

class TestSendTooFast:
    """ERR028: sent to the same number within 15 seconds."""

    def test_rate_limit_error_explains_15_second_rule(self):
        resp = {"result": "ERROR", "code": "ERR028", "description": "Too fast."}
        with patch("kwtsms._core._request", return_value=resp):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert "action" in result
        assert "15 second" in result["action"]


# ── Sender ID banned (ERR008) ─────────────────────────────────────────────────

class TestSenderIDBanned:
    """ERR008: the specified sender ID is banned."""

    def test_banned_sender_id_returns_error_with_action(self):
        resp = {"result": "ERROR", "code": "ERR008", "description": "SenderID is banned."}
        with patch("kwtsms._core._request", return_value=resp):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert "action" in result
        assert "sender ID" in result["action"].lower() or "sender id" in result["action"].lower()


# ── Emoji-only message returns ERR009 locally ─────────────────────────────────

class TestEmptyMessageAfterCleaning:
    """send() must return ERR009 locally when message is empty after clean_message."""

    def test_emoji_only_returns_err009(self):
        result = _client().send("96598765432", "🎉🎊🚀")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR009"

    def test_emoji_only_has_action(self):
        result = _client().send("96598765432", "🎉")
        assert "action" in result
        assert len(result["action"]) > 0

    def test_emoji_only_does_not_call_api(self):
        with patch("kwtsms._core._request") as mock_req:
            _client().send("96598765432", "🎉🎊")
        mock_req.assert_not_called()

    def test_emoji_only_bulk_path_returns_err009(self):
        """Emoji-only message on bulk path (>200 numbers) must also return ERR009 locally."""
        numbers = [f"9659{str(i).zfill(7)}" for i in range(201)]
        with patch("kwtsms._core._request") as mock_req:
            result = _client().send(numbers, "🎉🎊")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR009"
        mock_req.assert_not_called()

    def test_invisible_chars_only_returns_err009(self):
        """Message of only zero-width spaces becomes empty and returns ERR009."""
        result = _client().send("96598765432", "\u200B\u200C\u200D")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR009"

    def test_normal_message_not_affected(self):
        """A plain text message must NOT trigger ERR009."""
        with patch("kwtsms._core._request", return_value={
            "result": "OK", "msg-id": "x", "numbers": 1,
            "points-charged": 1, "balance-after": 99,
        }):
            result = _client().send("96598765432", "Hello")
        assert result["result"] == "OK"


# ── Network failure on send ───────────────────────────────────────────────────

class TestNetworkFailureOnSend:
    """send() must return a dict on network failure, never raise."""

    def test_network_error_returns_error_dict(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Connection refused")):
            result = _client().send("96598765432", "Test")
        assert isinstance(result, dict)
        assert result["result"] == "ERROR"

    def test_network_error_has_code(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Connection refused")):
            result = _client().send("96598765432", "Test")
        assert result.get("code") == "NETWORK"

    def test_network_error_has_description(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Connection refused")):
            result = _client().send("96598765432", "Test")
        assert "Connection refused" in result.get("description", "")

    def test_network_error_has_action(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Connection refused")):
            result = _client().send("96598765432", "Test")
        assert "action" in result
        assert len(result["action"]) > 0


# ── coverage() network error ──────────────────────────────────────────────────

class TestCoverageNetworkError:
    """coverage() must include action on network errors, consistent with senderids()."""

    def test_coverage_network_error_has_action(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Timeout")):
            result = _client().coverage()
        assert result["result"] == "ERROR"
        assert "action" in result
        assert len(result["action"]) > 0

    def test_coverage_network_error_returns_dict_not_exception(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Timeout")):
            result = _client().coverage()
        assert isinstance(result, dict)


# ── purchased property ────────────────────────────────────────────────────────

class TestPurchasedProperty:
    """KwtSMS.purchased exposes _cached_purchased without breaking encapsulation."""

    BALANCE_RESPONSE = {"result": "OK", "available": 50.0, "purchased": 200.0}

    def test_purchased_is_none_before_verify(self):
        assert _client().purchased is None

    def test_purchased_is_set_after_verify(self):
        with patch("kwtsms._core._request", return_value=self.BALANCE_RESPONSE):
            sms = _client()
            sms.verify()
        assert sms.purchased == 200.0

    def test_purchased_property_exists(self):
        assert hasattr(_client(), "purchased")


# ── Unknown / unmapped error code ─────────────────────────────────────────────

class TestUnknownErrorCode:
    """An error code not in our table should still return a clean result."""

    def test_unknown_error_code_does_not_crash(self):
        resp = {"result": "ERROR", "code": "ERR999", "description": "Unknown future error."}
        with patch("kwtsms._core._request", return_value=resp):
            result = _client().send("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR999"
        # no 'action' key. That's fine, we just don't add one for unknown codes
        assert "description" in result
