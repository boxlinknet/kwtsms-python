from kwtsms._core import parse_webhook

VALID_PAYLOAD = {
    "msg-id":       "abc123",
    "mobile":       "96598765432",
    "status":       "DELIVERED",
    "delivered-at": 1700000000,
}

class TestParseWebhook:
    def test_valid_payload_returns_parsed_dict(self):
        result = parse_webhook(VALID_PAYLOAD)
        assert result["ok"] is True
        assert result["msg_id"] == "abc123"
        assert result["phone"] == "96598765432"
        assert result["status"] == "DELIVERED"
        assert result["delivered_at"] == 1700000000

    def test_missing_msg_id_returns_error(self):
        result = parse_webhook({"mobile": "96598765432", "status": "DELIVERED"})
        assert result["ok"] is False
        assert "msg-id" in result["error"]

    def test_missing_status_returns_error(self):
        result = parse_webhook({"msg-id": "abc123", "mobile": "96598765432"})
        assert result["ok"] is False

    def test_empty_payload_returns_error(self):
        result = parse_webhook({})
        assert result["ok"] is False

    def test_non_dict_payload_returns_error(self):
        result = parse_webhook("not a dict")
        assert result["ok"] is False

    def test_known_statuses_accepted(self):
        for status in ("DELIVERED", "FAILED", "PENDING", "REJECTED"):
            payload = {**VALID_PAYLOAD, "status": status}
            result = parse_webhook(payload)
            assert result["ok"] is True

    def test_unknown_status_still_accepted(self):
        payload = {**VALID_PAYLOAD, "status": "UNKNOWN_NEW_STATUS"}
        result = parse_webhook(payload)
        assert result["ok"] is True
        assert result["status"] == "UNKNOWN_NEW_STATUS"
