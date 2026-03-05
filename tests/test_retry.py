from unittest.mock import patch
from kwtsms import KwtSMS

def _client(**kwargs) -> KwtSMS:
    defaults = dict(username="python_username", password="python_password",
                    sender_id="TEST", log_file="")
    defaults.update(kwargs)
    return KwtSMS(**defaults)

OK_RESPONSE     = {"result": "OK", "msg-id": "abc", "numbers": 1,
                   "points-charged": 1, "balance-after": 99.0}
ERR028_RESPONSE = {"result": "ERROR", "code": "ERR028",
                   "description": "Wait 15 seconds before resending."}

class TestSendWithRetry:
    def test_ok_on_first_attempt_no_sleep(self):
        with patch("kwtsms._core._request", return_value=OK_RESPONSE) as mock_req:
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client().send_with_retry("96598765432", "Test")
        assert result["result"] == "OK"
        mock_sleep.assert_not_called()

    def test_err028_triggers_sleep_and_retry(self):
        responses = [ERR028_RESPONSE, OK_RESPONSE]
        with patch("kwtsms._core._request", side_effect=responses):
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client().send_with_retry("96598765432", "Test")
        assert result["result"] == "OK"
        mock_sleep.assert_called_once_with(16)

    def test_err028_three_times_gives_up(self):
        with patch("kwtsms._core._request", return_value=ERR028_RESPONSE) as mock_req:
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client().send_with_retry("96598765432", "Test", max_retries=3)
        assert result["result"] == "ERROR"
        assert result["code"] == "ERR028"
        assert mock_sleep.call_count == 3
        assert mock_req.call_count == 4

    def test_max_retries_zero_never_sleeps(self):
        with patch("kwtsms._core._request", return_value=ERR028_RESPONSE):
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client().send_with_retry("96598765432", "Test", max_retries=0)
        assert result["code"] == "ERR028"
        mock_sleep.assert_not_called()

    def test_non_err028_error_not_retried(self):
        err010 = {"result": "ERROR", "code": "ERR010", "description": "Zero balance."}
        with patch("kwtsms._core._request", return_value=err010) as mock_req:
            with patch("kwtsms._core.time.sleep") as mock_sleep:
                result = _client().send_with_retry("96598765432", "Test")
        assert result["result"] == "ERROR"
        assert mock_req.call_count == 1
        mock_sleep.assert_not_called()
