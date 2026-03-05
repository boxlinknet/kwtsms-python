"""
Tests for _send_bulk() and the send() routing threshold (>200 numbers).

All tests mock _request(): no real network calls. time.sleep is also mocked
to keep the test suite fast.
"""
from unittest.mock import patch
import pytest
from kwtsms import KwtSMS


def _client(**kwargs) -> KwtSMS:
    defaults = dict(username="python_username", password="python_password", sender_id="TEST", log_file="")
    defaults.update(kwargs)
    return KwtSMS(**defaults)


def _nums(n: int):
    """Generate n unique valid phone numbers."""
    return [f"9659{str(i).zfill(7)}" for i in range(n)]


OK_RESPONSE = {
    "result": "OK", "msg-id": "abc123", "numbers": 200,
    "points-charged": 200, "balance-after": 800,
}

ERR013_RESPONSE = {
    "result": "ERROR", "code": "ERR013",
    "description": "Queue full.",
}

ERR010_RESPONSE = {
    "result": "ERROR", "code": "ERR010",
    "description": "Zero balance.",
}


# ── Routing threshold ──────────────────────────────────────────────────────────

class TestSendRoutingThreshold:
    """send() must route to _send_bulk only when len(valid_numbers) > 200."""

    def test_200_numbers_uses_single_request(self):
        """Exactly 200 numbers must NOT use _send_bulk."""
        with patch("kwtsms._core._request", return_value=OK_RESPONSE) as mock_req:
            _client().send(_nums(200), "Test")
        assert mock_req.call_count == 1

    def test_201_numbers_uses_bulk(self):
        """201 numbers must route to _send_bulk, which splits into 2 batches."""
        responses = [
            {**OK_RESPONSE, "numbers": 200},
            {**OK_RESPONSE, "numbers": 1},
        ]
        with patch("kwtsms._core._request", side_effect=responses) as mock_req:
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(201), "Test")
        assert result["bulk"] is True
        assert result["batches"] == 2
        assert mock_req.call_count == 2

    def test_400_numbers_splits_into_2_batches(self):
        responses = [{**OK_RESPONSE, "numbers": 200}, {**OK_RESPONSE, "numbers": 200}]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        assert result["batches"] == 2
        assert result["numbers"] == 400

    def test_401_numbers_splits_into_3_batches(self):
        responses = [
            {**OK_RESPONSE, "numbers": 200},
            {**OK_RESPONSE, "numbers": 200},
            {**OK_RESPONSE, "numbers": 1},
        ]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(401), "Test")
        assert result["batches"] == 3


# ── Bulk result statuses ───────────────────────────────────────────────────────

class TestSendBulkResults:
    """Verify OK / PARTIAL / ERROR overall status logic."""

    def test_all_batches_ok_returns_ok(self):
        responses = [{**OK_RESPONSE, "numbers": 200}, {**OK_RESPONSE, "numbers": 200}]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        assert result["result"] == "OK"
        assert result["errors"] == []

    def test_all_batches_fail_returns_error(self):
        responses = [ERR010_RESPONSE, ERR010_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        assert result["result"] == "ERROR"
        assert len(result["errors"]) == 2

    def test_partial_batches_returns_partial(self):
        """First batch OK, second fails: result must be PARTIAL."""
        responses = [OK_RESPONSE, ERR010_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        assert result["result"] == "PARTIAL"
        assert len(result["msg-ids"]) == 1
        assert len(result["errors"]) == 1

    def test_bulk_result_has_required_fields(self):
        responses = [OK_RESPONSE, OK_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        for field in ("result", "bulk", "batches", "numbers", "points-charged",
                      "balance-after", "msg-ids", "errors"):
            assert field in result, f"Missing field: {field}"

    def test_bulk_aggregates_msg_ids(self):
        responses = [
            {**OK_RESPONSE, "msg-id": "id1"},
            {**OK_RESPONSE, "msg-id": "id2"},
        ]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(400), "Test")
        assert "id1" in result["msg-ids"]
        assert "id2" in result["msg-ids"]

    def test_bulk_aggregates_points_charged(self):
        responses = [
            {**OK_RESPONSE, "points-charged": 200},
            {**OK_RESPONSE, "points-charged": 150},
        ]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(350), "Test")
        assert result["points-charged"] == 350

    def test_bulk_network_error_recorded_not_raised(self):
        """RuntimeError from _request must be recorded as NETWORK error, not crash."""
        with patch("kwtsms._core._request", side_effect=RuntimeError("Timeout")):
            with patch("kwtsms._core.time.sleep"):
                result = _client().send(_nums(201), "Test")
        assert result["result"] == "ERROR"
        assert any(e["code"] == "NETWORK" for e in result["errors"])


# ── ERR013 retry logic ─────────────────────────────────────────────────────────

class TestSendBulkERR013Retry:
    """ERR013 (queue full) should be retried up to 3x with backoff."""

    def test_err013_then_ok_succeeds(self):
        """ERR013 on first attempt, OK on second: should succeed."""
        responses = [ERR013_RESPONSE, OK_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client()._send_bulk(_nums(1), "Test", "TEST")
        assert result["result"] == "OK"
        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert 30 in sleep_calls

    def test_err013_three_times_then_ok(self):
        """ERR013 three times, OK on fourth: should succeed on the last retry."""
        responses = [ERR013_RESPONSE, ERR013_RESPONSE, ERR013_RESPONSE, OK_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client()._send_bulk(_nums(1), "Test", "TEST")
        assert result["result"] == "OK"

    def test_err013_four_times_gives_up(self):
        """ERR013 on all 4 attempts: should give up and return ERROR."""
        responses = [ERR013_RESPONSE] * 4
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep"):
                result = _client()._send_bulk(_nums(1), "Test", "TEST")
        assert result["result"] == "ERROR"
        assert len(result["errors"]) == 1

    def test_err013_retry_uses_correct_backoff_waits(self):
        """Retry waits must be 30s, 60s, 120s in that order."""
        responses = [ERR013_RESPONSE, ERR013_RESPONSE, ERR013_RESPONSE, OK_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                _client()._send_bulk(_nums(1), "Test", "TEST")
        # Filter out inter-batch sleep (0.5s): only 1 batch here so none expected
        retry_sleeps = [c.args[0] for c in mock_sleep.call_args_list if c.args[0] != 0.5]
        assert retry_sleeps == [30, 60, 120]

    def test_non_err013_error_does_not_retry(self):
        """ERR010 (zero balance) must NOT trigger a retry."""
        with patch("kwtsms._core._request", return_value=ERR010_RESPONSE) as mock_req:
            with patch("kwtsms._core.time.sleep"):
                _client()._send_bulk(_nums(1), "Test", "TEST")
        assert mock_req.call_count == 1
