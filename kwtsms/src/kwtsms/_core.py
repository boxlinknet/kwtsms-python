"""
kwtsms._core — kwtSMS API client logic.
Zero external dependencies. Python 3.8+
"""

import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://www.kwtsms.com/API/"

# kwtSMS server runs at GMT+3 (Asia/Kuwait).
# unix-timestamp values in API responses are server time, not UTC.
SERVER_TIMEZONE = "Asia/Kuwait (GMT+3)"


# ── Phone normalization ────────────────────────────────────────────────────────

def normalize_phone(phone: str) -> str:
    """Normalize phone to kwtSMS format: digits only, no leading zeros."""
    # 1. Convert Arabic-Indic and Extended Arabic-Indic digits to Latin
    phone = phone.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'))
    # 2. Strip every non-digit character (spaces, +, dashes, dots, brackets, etc.)
    phone = re.sub(r'\D', '', phone)
    # 3. Strip leading zeros (handles 00 country code prefix)
    phone = phone.lstrip('0')
    return phone


# ── Message cleaning ──────────────────────────────────────────────────────────

def clean_message(text: str) -> str:
    """
    Clean SMS message text before sending to kwtSMS.

    Called automatically by KwtSMS.send() — no manual call needed.

    Strips content that silently breaks delivery:
    - Arabic-Indic / Extended Arabic-Indic digits → Latin digits
    - Emojis and pictographic symbols (silently stuck in queue)
    - Hidden control characters: BOM, zero-width space, soft hyphen, etc.
    - HTML tags (causes ERR027)

    Does NOT strip Arabic letters — Arabic text is fully supported.
    """
    # 1. Convert Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) and
    #    Extended Arabic-Indic / Persian digits (۰۱۲۳۴۵۶۷۸۹) to Latin
    text = text.translate(str.maketrans(
        '٠١٢٣٤٥٦٧٨٩'
        '۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789'
    ))

    # 2. Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # 3. Remove emojis and pictographic characters across major Unicode ranges
    def _is_safe(char: str) -> bool:
        cp = ord(char)
        return not (
            0x1F600 <= cp <= 0x1F64F
            or 0x1F300 <= cp <= 0x1F5FF
            or 0x1F680 <= cp <= 0x1F6FF
            or 0x1F700 <= cp <= 0x1F77F
            or 0x1F780 <= cp <= 0x1F7FF
            or 0x1F800 <= cp <= 0x1F8FF
            or 0x1F900 <= cp <= 0x1F9FF
            or 0x1FA00 <= cp <= 0x1FA6F
            or 0x1FA70 <= cp <= 0x1FAFF
            or 0x2600 <= cp <= 0x26FF
            or 0x2700 <= cp <= 0x27BF
            or 0xFE00 <= cp <= 0xFE0F
        )

    text = ''.join(c for c in text if _is_safe(c))

    # 4. Strip specific hidden / invisible characters by codepoint
    HIDDEN = {'\u200B', '\u200C', '\u200D', '\u2060', '\u00AD', '\uFEFF', '\uFFFC'}
    text = ''.join(c for c in text if c not in HIDDEN)

    # 5. Strip remaining Unicode control characters (Cc/Cf),
    #    preserving \n and \t which SMS supports
    text = ''.join(
        c for c in text
        if c in ('\n', '\t') or unicodedata.category(c) not in ('Cc', 'Cf')
    )

    return text


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env_file(env_file: str = ".env") -> dict:
    """Load key=value pairs from a .env file. Returns empty dict if not found."""
    env: dict = {}
    try:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


# ── JSONL logger ──────────────────────────────────────────────────────────────

def _write_log(log_file: str, entry: dict) -> None:
    """Append a JSONL log entry. Never raises — logging must not break main flow."""
    if not log_file:
        return
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ── HTTP request ──────────────────────────────────────────────────────────────

def _request(endpoint: str, payload: dict, log_file: str = "") -> dict:
    """
    POST to a kwtSMS REST/JSON API endpoint.

    - Always sets Content-Type and Accept: application/json
    - Strips password from log entry
    - Returns parsed JSON dict
    - Raises RuntimeError on network / HTTP / parse failure
    """
    url = BASE_URL + endpoint + "/"
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    safe_payload = {k: ("***" if k == "password" else v) for k, v in payload.items()}
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "request": safe_payload,
        "response": None,
        "ok": False,
        "error": None,
    }

    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            log_entry["response"] = data
            log_entry["ok"] = data.get("result") == "OK"
            _write_log(log_file, log_entry)
            return data

    except HTTPError as e:
        err = f"HTTP {e.code}: {e.reason}"
        log_entry["error"] = err
        _write_log(log_file, log_entry)
        raise RuntimeError(err) from e

    except URLError as e:
        err = f"Network error: {e.reason}"
        log_entry["error"] = err
        _write_log(log_file, log_entry)
        raise RuntimeError(err) from e

    except json.JSONDecodeError as e:
        err = f"Invalid JSON response: {e}"
        log_entry["error"] = err
        _write_log(log_file, log_entry)
        raise RuntimeError(err) from e


# ── KwtSMS class ──────────────────────────────────────────────────────────────

class KwtSMS:
    """
    kwtSMS API client. Zero external dependencies. Python 3.8+

    Server timezone: Asia/Kuwait (GMT+3).
    unix-timestamp values in API responses are GMT+3 server time, not UTC.
    Log timestamps written by this client are always UTC ISO-8601.

    Quick start:
        sms = KwtSMS.from_env()
        ok, balance, err = sms.verify()
        result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
        result = sms.send("96598765432", "Hello", sender="OTHER-ID")
        report = sms.validate(["96598765432", "+96512345678"])
        balance = sms.balance()
    """

    def __init__(
        self,
        username: str,
        password: str,
        sender_id: str = "KWT-SMS",
        test_mode: bool = False,
        log_file: str = "kwtsms.log",
    ):
        """
        Args:
            username:  API username (not your account phone number).
            password:  API password.
            sender_id: Sender ID shown on recipient's phone. Defaults to "KWT-SMS"
                       which is fine for testing but MUST be replaced with your
                       private registered sender ID before going live.
            test_mode: When True, messages are queued but not delivered and no
                       credits are consumed. Safe for development. Default False.
            log_file:  Path to JSONL log file. Set to "" to disable logging.
        """
        if not username or not password:
            raise ValueError("username and password are required")
        self.username = username
        self.password = password
        self.sender_id = sender_id
        self.test_mode = test_mode
        self.log_file = log_file
        self._cached_balance: Optional[float] = None

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "KwtSMS":
        """
        Load credentials from environment variables, falling back to .env file.

        Required env vars:
            KWTSMS_USERNAME   — API username (not your account phone number)
            KWTSMS_PASSWORD   — API password

        Optional env vars:
            KWTSMS_SENDER_ID  — Sender ID (default: "KWT-SMS", fine for testing)
            KWTSMS_TEST_MODE  — "1" to queue without delivering (default: "0")
            KWTSMS_LOG_FILE   — JSONL log path (default: "kwtsms.log")
        """
        file_env = _load_env_file(env_file)

        def get(key: str, default: str = "") -> str:
            return os.environ.get(key) or file_env.get(key) or default

        username  = get("KWTSMS_USERNAME")
        password  = get("KWTSMS_PASSWORD")
        sender_id = get("KWTSMS_SENDER_ID", "KWT-SMS")
        test_mode = get("KWTSMS_TEST_MODE", "0") == "1"
        log_file  = get("KWTSMS_LOG_FILE", "kwtsms.log")

        missing = [k for k, v in {
            "KWTSMS_USERNAME": username,
            "KWTSMS_PASSWORD": password,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing credentials: {', '.join(missing)}")

        return cls(username, password, sender_id, test_mode, log_file)

    def _creds(self) -> dict:
        return {"username": self.username, "password": self.password}

    # ── verify ────────────────────────────────────────────────────────────────

    def verify(self) -> tuple:
        """
        Test credentials by calling /balance/.
        Returns: (ok: bool, balance: float | None, error: str | None)
        """
        try:
            data = _request("balance", self._creds(), self.log_file)
            if data.get("result") == "OK":
                self._cached_balance = float(data.get("available", 0))
                return True, self._cached_balance, None
            return False, None, data.get("description", data.get("code", "Unknown error"))
        except RuntimeError as e:
            return False, None, str(e)

    # ── balance ───────────────────────────────────────────────────────────────

    def balance(self) -> Optional[float]:
        """
        Get current balance via /balance/ API call.
        Returns None on error (returns cached value if available).
        Also updated automatically after every successful send().
        """
        ok, bal, _ = self.verify()
        return bal if ok else self._cached_balance

    # ── validate ──────────────────────────────────────────────────────────────

    def validate(self, phones: List[str]) -> dict:
        """
        Validate and normalize phone numbers via /validate/.

        Returns:
            {
                "ok":    [...],  # valid and routable
                "er":    [...],  # format error
                "nr":    [...],  # no route (country not activated)
                "raw":   {...},  # full API response
                "error": None,   # set on network / API error
            }
        """
        normalized = [normalize_phone(str(p)) for p in phones]
        normalized = [n for n in normalized if n]

        if not normalized:
            return {"ok": [], "er": [], "nr": [], "raw": None,
                    "error": "No valid numbers after normalization"}

        payload = {**self._creds(), "mobile": ",".join(normalized)}
        try:
            data = _request("validate", payload, self.log_file)
            if data.get("result") == "OK":
                mobile = data.get("mobile", {})
                return {
                    "ok":    mobile.get("OK", []),
                    "er":    mobile.get("ER", []),
                    "nr":    mobile.get("NR", []),
                    "raw":   data,
                    "error": None,
                }
            return {"ok": [], "er": normalized, "nr": [], "raw": data,
                    "error": data.get("description")}
        except RuntimeError as e:
            return {"ok": [], "er": normalized, "nr": [], "raw": None, "error": str(e)}

    # ── send ──────────────────────────────────────────────────────────────────

    def send(
        self,
        mobile: Union[str, List[str]],
        message: str,
        sender: Optional[str] = None,
    ) -> dict:
        """
        Send SMS to one or more numbers.

        Args:
            mobile:  Phone number string or list of strings. Normalized automatically
                     (strips +, 00, spaces, dashes, Arabic/Hindi digits).
            message: SMS text. Cleaned automatically (strips emojis, hidden chars,
                     HTML, converts Arabic/Hindi digits to Latin).
            sender:  Optional Sender ID for this call only. Overrides self.sender_id.
                     Defaults to self.sender_id (from constructor / .env).

        Returns for ≤200 numbers (raw API response):
            OK:    {"result":"OK", "msg-id":"...", "numbers":1,
                    "points-charged":1, "balance-after":180, "unix-timestamp":...}
            ERROR: {"result":"ERROR", "code":"ERR...", "description":"..."}

        Returns for >200 numbers (aggregated bulk result):
            OK:      {"result":"OK",      "bulk":True, "batches":5, "msg-ids":[...],
                      "numbers":950, "points-charged":950, "balance-after":175, "errors":[]}
            PARTIAL: {"result":"PARTIAL", "bulk":True, ...}
            ERROR:   {"result":"ERROR",   "bulk":True, ...}

        Note: result["unix-timestamp"] is GMT+3 server time. Log entries use UTC.

        Raises:
            RuntimeError: on network / HTTP failure (single send only;
                          bulk captures errors per batch).
        """
        effective_sender = sender or self.sender_id

        if isinstance(mobile, list):
            numbers = [normalize_phone(str(p)) for p in mobile]
        else:
            numbers = [normalize_phone(str(mobile))]
        numbers = [n for n in numbers if n]

        if not numbers:
            return {"result": "ERROR", "code": "ERR006",
                    "description": "No valid numbers after normalization"}

        if len(numbers) > 200:
            return self._send_bulk(numbers, message, effective_sender)

        payload = {
            **self._creds(),
            "sender":  effective_sender,
            "mobile":  ",".join(numbers),
            "message": clean_message(message),
            "test":    "1" if self.test_mode else "0",
        }

        data = _request("send", payload, self.log_file)

        if data.get("result") == "OK" and "balance-after" in data:
            self._cached_balance = float(data["balance-after"])

        return data

    # ── _send_bulk ────────────────────────────────────────────────────────────

    def _send_bulk(self, numbers: List[str], message: str, sender: str) -> dict:
        """
        Internal: send to >200 pre-normalized numbers in batches of 200.
        Called automatically by send() — do not call directly.

        Rate: 0.5s between batches (≤ 2 req/sec, within kwtSMS safe limit).
        ERR013 (queue full): retries up to 3× with 30s / 60s / 120s backoff.
        """
        BATCH_SIZE   = 200
        BATCH_DELAY  = 0.5
        ERR013_WAIT  = [30, 60, 120]

        message = clean_message(message)
        batches = [numbers[i:i + BATCH_SIZE] for i in range(0, len(numbers), BATCH_SIZE)]
        total_batches = len(batches)

        msg_ids:      List[str]  = []
        errors:       List[dict] = []
        total_nums   = 0
        total_pts    = 0
        last_balance: Optional[float] = None

        for i, batch in enumerate(batches):
            payload = {
                **self._creds(),
                "sender":  sender,
                "mobile":  ",".join(batch),
                "message": message,
                "test":    "1" if self.test_mode else "0",
            }

            data = None
            for attempt, wait in enumerate([0] + ERR013_WAIT):
                if wait:
                    time.sleep(wait)
                try:
                    data = _request("send", payload, self.log_file)
                except RuntimeError as e:
                    errors.append({"batch": i + 1, "code": "NETWORK", "description": str(e)})
                    data = None
                    break
                if data.get("code") != "ERR013" or attempt == len(ERR013_WAIT):
                    break

            if data and data.get("result") == "OK":
                msg_ids.append(data.get("msg-id", ""))
                total_nums += int(data.get("numbers", len(batch)))
                total_pts  += int(data.get("points-charged", 0))
                if "balance-after" in data:
                    last_balance = float(data["balance-after"])
                    self._cached_balance = last_balance
            elif data and data.get("result") == "ERROR":
                errors.append({
                    "batch":       i + 1,
                    "code":        data.get("code"),
                    "description": data.get("description"),
                })

            if i < total_batches - 1:
                time.sleep(BATCH_DELAY)

        ok_count = len(msg_ids)
        if ok_count == total_batches:
            overall = "OK"
        elif ok_count == 0:
            overall = "ERROR"
        else:
            overall = "PARTIAL"

        return {
            "result":         overall,
            "bulk":           True,
            "batches":        total_batches,
            "numbers":        total_nums,
            "points-charged": total_pts,
            "balance-after":  last_balance,
            "msg-ids":        msg_ids,
            "errors":         errors,
        }
