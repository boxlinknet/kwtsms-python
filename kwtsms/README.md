# kwtsms

Python client for the [kwtSMS API](https://kwtsms.com) — Kuwait SMS gateway.

Zero external dependencies. Python 3.8+.

---

kwtSMS is a Kuwaiti SMS gateway trusted by top businesses to deliver messages anywhere in the world, with private Sender ID, free API testing, non-expiring credits, and competitive flat-rate pricing. Secure, simple to integrate, built to last.

Open a free account in under 1 minute — no paperwork or payment required. 🚀 [Click here to get started →](https://www.kwtsms.com/signup/)

---

## Install

```bash
pip install kwtsms
uv add kwtsms
poetry add kwtsms
```

---

## Setup

Create a `.env` file in your project root (or set the same keys as environment variables):

```ini
KWTSMS_USERNAME=your_api_user
KWTSMS_PASSWORD=your_api_pass
KWTSMS_SENDER_ID=YOUR-SENDERID   # use KWT-SMS for testing only
KWTSMS_TEST_MODE=1                # 1 = test (safe default), 0 = live
KWTSMS_LOG_FILE=kwtsms.log        # JSONL log path, set to "" to disable
```

Or run the interactive setup wizard (verifies credentials and lists your sender IDs):

```bash
kwtsms setup
```

---

## Quick start

```python
from kwtsms import KwtSMS

# Load from .env or environment variables
sms = KwtSMS.from_env()

# Or construct directly
sms = KwtSMS(
    username="your_api_user",
    password="your_api_pass",
    sender_id="YOUR-SENDERID",  # default "KWT-SMS" (testing only)
    test_mode=False,             # default False
    log_file="kwtsms.log",       # default "kwtsms.log", "" to disable
)
```

---

## Methods

### `verify()` → `(ok, balance, error)`

Tests credentials by calling the balance endpoint.

```python
ok, balance, error = sms.verify()
if ok:
    print(f"Balance: {balance}")   # float
else:
    print(error)  # "Authentication error... → Check KWTSMS_USERNAME..."
```

Returns `(True, float, None)` on success, `(False, None, str)` on failure. Never raises.

---

### `balance()` → `float | None`

Returns current balance. Returns `None` on error (does not raise).
Also updated automatically after every successful `send()` — no need to call this after sending.

```python
bal = sms.balance()
```

---

### `send(mobile, message, sender=None)` → `dict`

Send SMS to one or more numbers.

```python
# Single number
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")

# Multiple numbers (list)
result = sms.send(["96598765432", "+96512345678", "0096511111111"], "Hello!")

# Override sender ID for this call only
result = sms.send("96598765432", "Hello", sender="MY-APP")
```

**Phone numbers** are normalized automatically: strips `+`, `00`, spaces, dashes; converts Arabic/Hindi digits to Latin.

**Message text** is cleaned automatically: strips emojis, hidden control characters (BOM, zero-width space, soft hyphen), HTML tags; converts Arabic/Hindi digits to Latin.

**OK response (≤200 numbers):**
```python
{
    "result":         "OK",
    "msg-id":         "f4c841adee210f31...",  # save this — needed for status/DLR lookups
    "numbers":        1,
    "points-charged": 1,
    "balance-after":  149,                    # save this — no need to call balance() again
    "unix-timestamp": 1741000800,             # ⚠ GMT+3 server time, NOT UTC
}
```

**ERROR response:**
```python
{
    "result":      "ERROR",
    "code":        "ERR003",
    "description": "Authentication error, username or password are not correct.",
    "action":      "Check KWTSMS_USERNAME and KWTSMS_PASSWORD...",  # always present
}
```

**Mixed valid/invalid input** — invalid numbers are reported, not raised:
```python
result = sms.send(["96598765432", "abc", "user@gmail.com"], "Hello")
# result["invalid"] → [
#   {"input": "abc",            "error": "'abc' is not a valid phone number — no digits found"},
#   {"input": "user@gmail.com", "error": "'user@gmail.com' is an email address, not a phone number"},
# ]
```

**Raises** `RuntimeError` on network/HTTP failure (single send only — bulk captures errors per batch).

---

### Bulk send (>200 numbers)

`send()` detects the count automatically and batches in groups of 200. No special call needed.

```python
result = sms.send(list_of_1000_numbers, "Hello!")

if result.get("bulk"):
    print(result["result"])          # "OK", "PARTIAL", or "ERROR"
    print(result["batches"])         # 5  (number of API calls made)
    print(result["numbers"])         # 950 (total numbers accepted)
    print(result["points-charged"])  # 950 (total credits used)
    print(result["balance-after"])   # balance after last batch
    print(result["msg-ids"])         # ["abc123", "def456", ...]  one per batch
    for err in result["errors"]:
        print(err["batch"], err["code"], err["description"])
```

- Rate: 0.5s between batches (≤2 req/s)
- ERR013 (queue full): auto-retries up to 3× with 30s / 60s / 120s backoff
- `"PARTIAL"` means some batches succeeded and some failed — check `errors`

---

### `validate(phones)` → `dict`

Validate phone numbers before sending. Numbers that fail local validation (email, too short, no digits) are rejected before any API call.

```python
report = sms.validate(["96598765432", "+96512345678", "abc", "123"])

report["ok"]       # ["96598765432", "96512345678"]  — valid and routable
report["er"]       # ["abc", "123"]                  — format error
report["nr"]       # []                              — no route for country
report["rejected"] # [{"input": "abc",  "error": "..."},
                   #  {"input": "123",  "error": "'123' is too short..."}]
report["error"]    # None if API call succeeded
report["raw"]      # full raw API response dict, or None if no API call was made
```

---

## Utility functions

```python
from kwtsms import normalize_phone, validate_phone_input, clean_message

# Normalize a phone number — strips +, 00, spaces, dashes; converts Arabic digits
normalize_phone("+96598765432")      # → "96598765432"
normalize_phone("00 965 9876-5432") # → "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")     # → "96598765432"

# Validate a phone number — returns (is_valid, error, normalized)
ok, error, number = validate_phone_input("+96598765432")
# → (True, None, "96598765432")

ok, error, number = validate_phone_input("user@gmail.com")
# → (False, "'user@gmail.com' is an email address, not a phone number", "")

ok, error, number = validate_phone_input("123")
# → (False, "'123' is too short to be a valid phone number (3 digits, minimum is 7)", "123")

# Clean message text — also called automatically inside send()
clean_message("Your OTP is: ١٢٣٤٥٦ 🎉")  # → "Your OTP is: 123456 "
```

---

## CLI

```bash
kwtsms setup                                          # first-time wizard
kwtsms verify                                         # test credentials + show balance
kwtsms balance                                        # check balance
kwtsms send 96598765432 "Your OTP is: 123456"        # send SMS
kwtsms send 96598765432,96512345678 "Hello!"          # multiple numbers (no spaces around commas)
kwtsms send "96598765432, 96512345678" "Hello!"       # or quote the list (spaces OK inside quotes)
kwtsms send 96598765432 "Hello" --sender MY-APP       # override sender ID
kwtsms send 96598765432 "Hello" --sender "kwt sms"   # sender ID with spaces — quote it
kwtsms validate 96598765432 +96512345678 0096511111111
```

---

## Error handling

Every API error response includes an `action` field with developer-friendly guidance:

```python
try:
    result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
except RuntimeError as e:
    # Network/HTTP failure — log and retry
    print(f"Network error: {e}")
else:
    if result["result"] == "OK":
        save_to_db(msg_id=result["msg-id"], balance=result["balance-after"])
    else:
        print(result["code"])        # e.g. "ERR010"
        print(result["description"]) # "Account balance is zero."
        print(result["action"])      # "Top up your kwtSMS account at kwtsms.com."
```

Common error codes:

| Code | Meaning |
|------|---------|
| `ERR003` | Wrong username or password |
| `ERR008` | Sender ID is banned / not registered |
| `ERR010` | Zero balance |
| `ERR011` | Insufficient balance |
| `ERR024` | Your IP is not in the API whitelist |
| `ERR025` | Invalid phone number format |
| `ERR026` | No route for this country (international not activated) |
| `ERR028` | Must wait 15s before sending to the same number again |

---

## Test mode

Set `KWTSMS_TEST_MODE=1` or `test_mode=True` — messages are queued but **not delivered**, no credits consumed.

```python
sms = KwtSMS.from_env()   # KWTSMS_TEST_MODE=1 in .env
result = sms.send("96598765432", "Test message")
# Message is queued — visible in kwtsms.com → Account → Queue
# Delete it from the queue to recover credits
```

Set `KWTSMS_TEST_MODE=0` before going live.

---

## Sender ID

`KWT-SMS` is a shared sender for **testing only** — it can cause delays and is blocked on some Kuwait carriers. Register a private sender ID on [kwtsms.com](https://kwtsms.com) before going live.

Use a **Transactional** sender ID for OTP/alerts to ensure delivery to DND numbers. Promotional sender IDs are silently blocked for DND subscribers (credits still deducted).

---

## Logging

One JSON line per API call written to `kwtsms.log` (or the path in `KWTSMS_LOG_FILE`). Password is always masked.

```json
{"ts":"2026-03-04T10:00:00+00:00","endpoint":"send","request":{"username":"myuser","password":"***","sender":"MYAPP","mobile":"96598765432","message":"Your OTP is: 123456","test":"0"},"response":{"result":"OK","msg-id":"f4c841ad...","numbers":1,"points-charged":1,"balance-after":149,"unix-timestamp":1741082400},"ok":true,"error":null}
```

> `ts` is always **UTC**. `unix-timestamp` inside `response` is **GMT+3** (Asia/Kuwait server time).

Set `log_file=""` or `KWTSMS_LOG_FILE=` to disable logging.

---

## License

MIT
