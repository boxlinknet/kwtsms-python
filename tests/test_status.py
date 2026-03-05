from unittest.mock import patch
from kwtsms import KwtSMS

def _client(**kwargs) -> KwtSMS:
    defaults = dict(username="python_username", password="python_password",
                    sender_id="TEST", log_file="")
    defaults.update(kwargs)
    return KwtSMS(**defaults)

OK_RESPONSE = {
    "result": "OK",
    "msg-id": "abc123",
    "status": "DELIVERED",
    "delivered-at": 1700000000,
}

ERR020_RESPONSE = {
    "result": "ERROR",
    "code": "ERR020",
    "description": "Message ID does not exist.",
}

class TestStatus:
    def test_status_ok_returns_dict_with_result_ok(self):
        with patch("kwtsms._core._request", return_value=OK_RESPONSE):
            result = _client().status("abc123")
        assert result["result"] == "OK"
        assert result["msg-id"] == "abc123"
        assert result["status"] == "DELIVERED"

    def test_status_error_has_action(self):
        with patch("kwtsms._core._request", return_value=ERR020_RESPONSE):
            result = _client().status("bad-id")
        assert result["result"] == "ERROR"
        assert "action" in result

    def test_status_network_error_returns_dict(self):
        with patch("kwtsms._core._request", side_effect=RuntimeError("Timeout")):
            result = _client().status("abc123")
        assert result["result"] == "ERROR"
        assert result["code"] == "NETWORK"
