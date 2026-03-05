"""
kwtsms._core: kwtSMS API client logic.
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


# ── API error messages ─────────────────────────────────────────────────────────
# Maps every kwtSMS error code to a developer-friendly action message.
# Appended as result["action"] on any ERROR response so callers know what to do.

_API_ERRORS: dict = {
    "ERR001": "API is disabled on this account. Enable it at kwtsms.com → Account → API.",
    "ERR002": "A required parameter is missing. Check that username, password, sender, mobile, and message are all provided.",
    "ERR003": "Wrong API username or password. Check KWTSMS_USERNAME and KWTSMS_PASSWORD. These are your API credentials, not your account mobile number.",
    "ERR004": "This account does not have API access. Contact kwtSMS support to enable it.",
    "ERR005": "This account is blocked. Contact kwtSMS support.",
    "ERR006": "No valid phone numbers. Make sure each number includes the country code (e.g., 96598765432 for Kuwait, not 98765432).",
    "ERR007": "Too many numbers in a single request (maximum 200). Split into smaller batches.",
    "ERR008": "This sender ID is banned or not found. Sender IDs are case sensitive (\"Kuwait\" is not the same as \"KUWAIT\"). Check your registered sender IDs at kwtsms.com.",
    "ERR009": "Message is empty. Provide a non-empty message text.",
    "ERR010": "Account balance is zero. Recharge credits at kwtsms.com.",
    "ERR011": "Insufficient balance for this send. Buy more credits at kwtsms.com.",
    "ERR012": "Message is too long (over 6 SMS pages). Shorten your message.",
    "ERR013": "Send queue is full (1000 messages). Wait a moment and try again.",
    "ERR019": "No delivery reports found for this message.",
    "ERR020": "Message ID does not exist. Make sure you saved the msg-id from the send response.",
    "ERR021": "No delivery report available for this message yet.",
    "ERR022": "Delivery reports are not ready yet. Try again after 24 hours.",
    "ERR023": "Unknown delivery report error. Contact kwtSMS support.",
    "ERR024": "Your IP address is not in the API whitelist. Add it at kwtsms.com → Account → API → IP Lockdown, or disable IP lockdown.",
    "ERR025": "Invalid phone number. Make sure the number includes the country code (e.g., 96598765432 for Kuwait, not 98765432).",
    "ERR026": "This country is not activated on your account. Contact kwtSMS support to enable the destination country.",
    "ERR027": "HTML tags are not allowed in the message. Remove any HTML content and try again.",
    "ERR028": "You must wait at least 15 seconds before sending to the same number again. No credits were consumed.",
    "ERR029": "Message ID does not exist or is incorrect.",
    "ERR030": "Message is stuck in the send queue with an error. Delete it at kwtsms.com → Queue to recover credits.",
    "ERR031": "Message rejected: bad language detected.",
    "ERR032": "Message rejected: spam detected.",
    "ERR033": "No active coverage found. Contact kwtSMS support.",
    "ERR_INVALID_INPUT": "One or more phone numbers are invalid. See details above.",
}


def _enrich_error(data: dict) -> dict:
    """
    Add an 'action' field to API error responses with developer-friendly guidance.
    Returns a new dict. Never mutates the original response.
    Has no effect on OK responses.
    """
    if data.get("result") != "ERROR":
        return data
    code = data.get("code", "")
    if code in _API_ERRORS:
        data = dict(data)
        data["action"] = _API_ERRORS[code]
    return data


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


# ── Phone input validation ────────────────────────────────────────────────────

def validate_phone_input(phone: str) -> tuple:
    """
    Validate a raw phone number input before sending to the kwtSMS API.

    Returns: (is_valid: bool, error: str | None, normalized: str)

    Catches every common mistake without crashing:
    - Empty or blank input
    - Email address entered instead of a phone number
    - Non-numeric text with no digits (e.g. "abc", "---")
    - Too short after normalization (< 7 digits)
    - Too long after normalization (> 15 digits, E.164 maximum)

    Examples:
        validate_phone_input("+96598765432")   → (True,  None,  "96598765432")
        validate_phone_input("")               → (False, "Phone number is required", "")
        validate_phone_input("user@gmail.com") → (False, "'user@gmail.com' is an email address, not a phone number", "")
        validate_phone_input("abc")            → (False, "'abc' is not a valid phone number, no digits found", "")
        validate_phone_input("123")            → (False, "'123' is too short ...", "123")
        validate_phone_input("1234567890123456") → (False, "'123...' is too long ...", "1234567890123456")
    """
    raw = str(phone).strip()

    # 1. Empty / blank
    if not raw:
        return False, "Phone number is required", ""

    # 2. Email address entered by mistake
    if "@" in raw:
        return False, f"'{raw}' is an email address, not a phone number", ""

    # 3. Normalize (Arabic digits → Latin, strip non-digits, strip leading zeros)
    normalized = normalize_phone(raw)

    # 4. No digits survived normalization (e.g. "abc", "---", "...")
    if not normalized:
        return False, f"'{raw}' is not a valid phone number, no digits found", ""

    # 5. Too short: any real phone number is at least 7 digits
    if len(normalized) < 7:
        return False, (
            f"'{raw}' is too short to be a valid phone number "
            f"({len(normalized)} digit{'s' if len(normalized) != 1 else ''}, minimum is 7)"
        ), normalized

    # 6. Too long: E.164 international standard allows a maximum of 15 digits
    if len(normalized) > 15:
        return False, (
            f"'{raw}' is too long to be a valid phone number "
            f"({len(normalized)} digits, maximum is 15)"
        ), normalized

    return True, None, normalized


# ── Message cleaning helpers (module-level to avoid per-call redefinition) ────

# Hidden / invisible characters that break SMS delivery
_HIDDEN_CHARS: frozenset = frozenset({
    '\u200B',  # zero-width space
    '\u200C',  # zero-width non-joiner
    '\u200D',  # zero-width joiner
    '\u2060',  # word joiner
    '\u00AD',  # soft hyphen
    '\uFEFF',  # BOM / zero-width no-break space
    '\uFFFC',  # object replacement character
})


def _char_is_sms_safe(cp: int) -> bool:
    """Return False for emoji and pictographic codepoints that break SMS delivery."""
    return not (
        0x1F600 <= cp <= 0x1F64F    # emoticons
        or 0x1F300 <= cp <= 0x1F5FF # misc symbols and pictographs
        or 0x1F680 <= cp <= 0x1F6FF # transport and map
        or 0x1F700 <= cp <= 0x1F77F # alchemical symbols
        or 0x1F780 <= cp <= 0x1F7FF # geometric shapes extended
        or 0x1F800 <= cp <= 0x1F8FF # supplemental arrows-C
        or 0x1F900 <= cp <= 0x1F9FF # supplemental symbols and pictographs
        or 0x1FA00 <= cp <= 0x1FA6F # chess symbols
        or 0x1FA70 <= cp <= 0x1FAFF # symbols and pictographs extended-A
        or 0x2600 <= cp <= 0x26FF   # miscellaneous symbols
        or 0x2700 <= cp <= 0x27BF   # dingbats
        or 0xFE00 <= cp <= 0xFE0F   # variation selectors
        # Extended emoji ranges
        or 0x1F000 <= cp <= 0x1F0FF # mahjong tiles + playing cards
        or 0x1F1E0 <= cp <= 0x1F1FF # regional indicator symbols (country flags)
        or cp == 0x20E3             # combining enclosing keycap (1️⃣ 2️⃣ etc.)
        or 0xE0000 <= cp <= 0xE007F # tags block (subdivision flags e.g. 🏴󠁧󠁢󠁥󠁮󠁧󠁿)
    )


# ── Message cleaning ──────────────────────────────────────────────────────────

def clean_message(text: str) -> str:
    """
    Clean SMS message text before sending to kwtSMS.

    Called automatically by KwtSMS.send(). No manual call needed.

    Strips content that silently breaks delivery:
    - Arabic-Indic / Extended Arabic-Indic digits → Latin digits
    - Emojis and pictographic symbols (silently stuck in queue), including:
      flags (regional indicators + tags block), keycap (U+20E3),
      mahjong/playing card tiles, and all standard emoji ranges
    - Hidden control characters: BOM, zero-width space, soft hyphen, etc.
    - HTML tags (causes ERR027)

    Does NOT strip Arabic letters. Arabic text is fully supported.
    Returns "" if the entire message was emoji or invisible characters.
    """
    # 1. Convert Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) and
    #    Extended Arabic-Indic / Persian digits (۰۱۲۳۴۵۶۷۸۹) to Latin
    text = text.translate(str.maketrans(
        '٠١٢٣٤٥٦٧٨٩'
        '۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789'
    ))

    # 2. Strip HTML tags. [^>] matches \n so multi-line tags are also stripped.
    text = re.sub(r'<[^>]+>', '', text)

    # 3. Remove emojis and pictographic characters across major Unicode ranges
    text = ''.join(c for c in text if _char_is_sms_safe(ord(c)))

    # 4. Strip specific hidden / invisible characters by codepoint
    text = ''.join(c for c in text if c not in _HIDDEN_CHARS)

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
                    val = value.strip()
                    # Strip one matching outer quote pair only (prevents mixed-quote corruption)
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                    env[key.strip()] = val
    except FileNotFoundError:
        pass
    return env


# ── JSONL logger ──────────────────────────────────────────────────────────────

def _write_log(log_file: str, entry: dict) -> None:
    """Append a JSONL log entry. Never raises. Logging must not break main flow."""
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
        # kwtSMS returns JSON error details (e.g. ERR003) in the 4xx response body.
        # Try to parse it: if it succeeds, return the JSON dict like a normal error
        # response instead of raising, so callers get a consistent dict every time.
        try:
            err_body = e.read().decode("utf-8")
            data = json.loads(err_body)
            log_entry["response"] = data
            log_entry["ok"] = False
            _write_log(log_file, log_entry)
            return data
        except Exception:
            pass
        # Body was not JSON, fall back to a plain HTTP error
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
        self._cached_purchased: Optional[float] = None

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "KwtSMS":
        """
        Load credentials from environment variables, falling back to .env file.

        Required env vars:
            KWTSMS_USERNAME   : API username (not your account phone number)
            KWTSMS_PASSWORD   : API password

        Optional env vars:
            KWTSMS_SENDER_ID  : Sender ID (default: "KWT-SMS", fine for testing)
            KWTSMS_TEST_MODE  : "1" to queue without delivering (default: "0")
            KWTSMS_LOG_FILE   : JSONL log path (default: "kwtsms.log")
        """
        file_env = _load_env_file(env_file)

        def get(key: str, default: str = "") -> str:
            # Use `is not None` so an explicit empty string (e.g. KWTSMS_LOG_FILE="")
            # is honored rather than falling through to the .env value or default.
            val = os.environ.get(key)
            if val is not None:
                return val
            val = file_env.get(key)
            if val is not None:
                return val
            return default

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

    @property
    def purchased(self) -> Optional[float]:
        """Purchased balance as returned by the last verify() or balance() call. None before first call."""
        return self._cached_purchased

    def _creds(self) -> dict:
        return {"username": self.username, "password": self.password}

    # ── verify ────────────────────────────────────────────────────────────────

    def verify(self) -> tuple:
        """
        Test credentials by calling /balance/.
        Returns: (ok: bool, balance: float | None, error: str | None)

        On failure, error includes both the API description and the action to take,
        e.g. "Authentication error... → Wrong API username or password. Check KWTSMS_..."
        """
        try:
            data = _request("balance", self._creds(), self.log_file)
            if data.get("result") == "OK":
                self._cached_balance = float(data.get("available", 0))
                self._cached_purchased = float(data.get("purchased", 0))
                return True, self._cached_balance, None
            data = _enrich_error(data)
            description = data.get("description", data.get("code", "Unknown error"))
            action = data.get("action")
            error = f"{description} → {action}" if action else description
            return False, None, error
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

    # ── senderids ─────────────────────────────────────────────────────────────

    def senderids(self) -> dict:
        """
        List sender IDs registered on this account via /senderid/.

        Returns a consistent dict. Never raises, never crashes.

        OK:    {"result": "OK",    "senderids": ["KWT-SMS", "MY-APP"]}
        ERROR: {"result": "ERROR", "code": "ERR003", "description": "...", "action": "..."}

        Example:
            result = sms.senderids()
            if result["result"] == "OK":
                print(result["senderids"])
            else:
                print(result["action"])
        """
        try:
            data = _request("senderid", self._creds(), self.log_file)
        except RuntimeError as e:
            return {"result": "ERROR", "code": "NETWORK", "description": str(e),
                    "action": "Check your internet connection and try again."}
        if data.get("result") == "OK":
            return {"result": "OK", "senderids": data.get("senderid", [])}
        return _enrich_error(data)

    # ── coverage ──────────────────────────────────────────────────────────────

    def coverage(self) -> dict:
        """
        List active country prefixes via /coverage/.

        Returns the full API response dict. On error the dict includes an
        'action' field with guidance (ERR033 = no active coverage).

        Example:
            result = sms.coverage()
            if result["result"] == "OK":
                print(result)  # country prefix data
            else:
                print(result["action"])
        """
        try:
            data = _request("coverage", self._creds(), self.log_file)
        except RuntimeError as e:
            return {"result": "ERROR", "code": "NETWORK", "description": str(e),
                    "action": "Check your internet connection and try again."}
        return _enrich_error(data)

    # ── validate ──────────────────────────────────────────────────────────────

    def validate(self, phones: List[str]) -> dict:
        """
        Validate and normalize phone numbers via /validate/.

        Numbers that fail local validation (empty, email, too short, too long, no digits)
        are rejected immediately with a clear error, before any API call is made.
        Numbers that pass local validation are sent to the kwtSMS /validate/ endpoint.

        Returns:
            {
                "ok":       [...],  # valid and routable (from API)
                "er":       [...],  # format error (from API + locally rejected)
                "nr":       [...],  # no route: country not activated on account
                "raw":      {...},  # full API response, or None if no API call was made
                "error":    None,   # set if the entire API call failed
                "rejected": [...],  # locally rejected numbers with specific error messages
                                    # e.g. [{"input": "abc", "error": "'abc' is not a valid..."}]
            }
        """
        valid_normalized: List[str] = []
        pre_rejected: List[dict] = []

        for raw in phones:
            is_valid, error, normalized = validate_phone_input(str(raw))
            if is_valid:
                valid_normalized.append(normalized)
            else:
                pre_rejected.append({"input": str(raw), "error": error})

        result: dict = {
            "ok":       [],
            "er":       [r["input"] for r in pre_rejected],
            "nr":       [],
            "raw":      None,
            "error":    None,
            "rejected": pre_rejected,
        }

        if not valid_normalized:
            result["error"] = (
                pre_rejected[0]["error"] if len(pre_rejected) == 1
                else f"All {len(pre_rejected)} phone numbers failed validation"
            )
            return result

        payload = {**self._creds(), "mobile": ",".join(valid_normalized)}
        try:
            data = _request("validate", payload, self.log_file)
            if data.get("result") == "OK":
                mobile = data.get("mobile", {})
                result["ok"]  = mobile.get("OK", [])
                result["er"]  = mobile.get("ER", []) + result["er"]
                result["nr"]  = mobile.get("NR", [])
                result["raw"] = data
            else:
                data = _enrich_error(data)
                result["er"]    = valid_normalized + result["er"]
                result["raw"]   = data
                result["error"] = data.get("description", data.get("code"))
                if data.get("action"):
                    result["error"] = f"{result['error']} → {data['action']}"
        except RuntimeError as e:
            result["er"]    = valid_normalized + result["er"]
            result["error"] = str(e)

        return result

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
        """
        effective_sender = sender or self.sender_id

        raw_list = mobile if isinstance(mobile, list) else [mobile]

        valid_numbers: List[str] = []
        invalid: List[dict] = []

        for raw in raw_list:
            is_valid, error, normalized = validate_phone_input(str(raw))
            if is_valid:
                valid_numbers.append(normalized)
            else:
                invalid.append({"input": str(raw), "error": error})

        if not valid_numbers:
            # Every number failed local validation. Return a clear error, never crash
            description = (
                invalid[0]["error"] if len(invalid) == 1
                else f"All {len(invalid)} phone numbers are invalid"
            )
            return _enrich_error({
                "result":      "ERROR",
                "code":        "ERR_INVALID_INPUT",
                "description": description,
                "invalid":     invalid,
            })

        # Clean message before routing so both paths see the same cleaned text,
        # and so an emoji-only message is caught locally before any API call.
        cleaned_message = clean_message(message)
        if not cleaned_message:
            return _enrich_error({
                "result":      "ERROR",
                "code":        "ERR009",
                "description": "Message is empty after cleaning (contained only emojis or invisible characters).",
            })

        if len(valid_numbers) > 200:
            result = self._send_bulk(valid_numbers, cleaned_message, effective_sender)
        else:
            payload = {
                **self._creds(),
                "sender":  effective_sender,
                "mobile":  ",".join(valid_numbers),
                "message": cleaned_message,
                "test":    "1" if self.test_mode else "0",
            }
            try:
                result = _request("send", payload, self.log_file)
            except RuntimeError as e:
                return {
                    "result":      "ERROR",
                    "code":        "NETWORK",
                    "description": str(e),
                    "action":      "Check your internet connection and try again.",
                }
            if result.get("result") == "OK" and "balance-after" in result:
                self._cached_balance = float(result["balance-after"])
            else:
                result = _enrich_error(result)

        # If some numbers were skipped, attach them so the caller knows
        if invalid:
            result["invalid"] = invalid

        return result

    # ── _send_bulk ────────────────────────────────────────────────────────────

    def _send_bulk(self, numbers: List[str], message: str, sender: str) -> dict:
        """
        Internal: send to >200 pre-normalized numbers in batches of 200.
        Called automatically by send(). Do not call directly.

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
