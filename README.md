# kwtsms Python

[![PyPI](https://img.shields.io/pypi/v/kwtsms)](https://pypi.org/project/kwtsms/)
[![Downloads](https://img.shields.io/pypi/dm/kwtsms)](https://pypi.org/project/kwtsms/)
[![Python](https://img.shields.io/pypi/pyversions/kwtsms)](https://pypi.org/project/kwtsms/)
[![License](https://img.shields.io/pypi/l/kwtsms)](https://github.com/boxlinknet/kwtsms-python/blob/master/LICENSE)
[![CI](https://github.com/boxlinknet/kwtsms-python/actions/workflows/ci.yml/badge.svg)](https://github.com/boxlinknet/kwtsms-python/actions/workflows/ci.yml)
[![CodeQL](https://github.com/boxlinknet/kwtsms-python/actions/workflows/codeql.yml/badge.svg)](https://github.com/boxlinknet/kwtsms-python/actions/workflows/codeql.yml)
[![GitGuardian](https://github.com/boxlinknet/kwtsms-python/actions/workflows/gitguardian.yml/badge.svg)](https://github.com/boxlinknet/kwtsms-python/actions/workflows/gitguardian.yml)

Official Python client for the [kwtSMS API](https://kwtsms.com), the Kuwait SMS gateway.

Zero external dependencies. Python 3.8+.

---

## About kwtSMS

kwtSMS is a Kuwaiti SMS gateway trusted by top businesses to deliver messages anywhere in the world, with private Sender ID, free API testing, non-expiring credits, and competitive flat-rate pricing. Secure, simple to integrate, built to last. Open a free account in under 1 minute, no paperwork or payment required. [Click here to get started](https://www.kwtsms.com/signup/) 👍

---

## Prerequisites

You need **Python 3.8 or newer** installed.

```bash
python3 --version
```

If you see a version number (e.g., `Python 3.12.3`), you're ready. If not, install Python:

- **All platforms:** Download from https://www.python.org/downloads/
- **macOS:** `brew install python`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install python3 python3-pip`
- **Windows:** Download from https://www.python.org/downloads/. Check "Add Python to PATH" during install

---

## Install

### Using pip (included with Python)

pip comes bundled with Python 3.4+. Verify it's available:

```bash
pip --version
```

If not found, try `pip3 --version`. If still missing:

```bash
python3 -m ensurepip --upgrade
```

Then install kwtsms:

```bash
pip install kwtsms
```

### Using uv (recommended for new projects)

uv is a fast Python package manager written in Rust. Install it first:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

Then install kwtsms:

```bash
uv add kwtsms
```

### Using poetry

Install poetry first if you don't have it:

```bash
# macOS / Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Or with pip
pip install poetry
```

Then install kwtsms:

```bash
poetry add kwtsms
```

### Using pipenv

Install pipenv first if you don't have it:

```bash
pip install pipenv
```

Then install kwtsms:

```bash
pipenv install kwtsms
```

---

## Quick start

```python
from kwtsms import KwtSMS

sms = KwtSMS.from_env()                                    # reads .env or env vars
ok, balance, error = sms.verify()                           # test credentials
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")  # send SMS
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

`from_env()` checks environment variables first, then the `.env` file as fallback.

---

## Credential Management

**Never hardcode credentials in your source code.** Credentials must be changeable without modifying code or redeploying.

```python
# Option 1: Environment variables / .env file (recommended)
sms = KwtSMS.from_env()

# Option 2: Constructor (for custom config systems, DI containers, etc.)
sms = KwtSMS(
    username="python_username",
    password="python_password",
    sender_id="YOUR-SENDERID",  # default "KWT-SMS" (testing only)
    test_mode=False,             # default False
    log_file="kwtsms.log",       # default "kwtsms.log", "" to disable
)
```

**For web apps and SaaS:** Provide an admin settings page where API credentials can be updated without touching code. Include a "Test Connection" button that calls `verify()`.

**For production:** Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) and pass credentials to the constructor.

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
    "msg-id":         "f4c841adee210f31...",  # save this: needed for status/DLR lookups
    "numbers":        1,
    "points-charged": 1,
    "balance-after":  149,                    # save this: no need to call balance() again
    "unix-timestamp": 1741000800,             # ⚠ GMT+3 server time, NOT UTC
}
```

**ERROR response:**
```python
{
    "result":      "ERROR",
    "code":        "ERR003",
    "description": "Authentication error, username or password are not correct.",
    "action":      "Wrong API username or password. Check KWTSMS_USERNAME and KWTSMS_PASSWORD...",
}
```

**Mixed valid/invalid input**: invalid numbers are reported, not raised:
```python
result = sms.send(["96598765432", "abc", "user@gmail.com"], "Hello")
# result["invalid"] → [
#   {"input": "abc",            "error": "'abc' is not a valid phone number, no digits found"},
#   {"input": "user@gmail.com", "error": "'user@gmail.com' is an email address, not a phone number"},
# ]
```

Never raises. Network failures are returned as `{"result": "ERROR", "code": "NETWORK", "description": "...", "action": "..."}`.

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
- `"PARTIAL"` means some batches succeeded and some failed. Check `errors`

---

### `balance()` → `float | None`

Returns current balance. Returns `None` on error (does not raise).
Also updated automatically after every successful `send()`, so no need to call this after sending.

```python
bal = sms.balance()
```

---

### `validate(phones)` → `dict`

Validate phone numbers before sending. Numbers that fail local validation (email, too short, no digits) are rejected before any API call.

```python
report = sms.validate(["96598765432", "+96512345678", "abc", "123"])

report["ok"]       # ["96598765432", "96512345678"]  : valid and routable
report["er"]       # ["abc", "123"]                  : format error
report["nr"]       # []                              : no route for country
report["rejected"] # [{"input": "abc",  "error": "..."},
                   #  {"input": "123",  "error": "'123' is too short..."}]
report["error"]    # None if API call succeeded
report["raw"]      # full raw API response dict, or None if no API call was made
```

---

### `senderids()` → `dict`

Returns the sender IDs registered on this account.

```python
result = sms.senderids()
if result["result"] == "OK":
    print(result["senderids"])  # → ["KWT-SMS", "MY-APP"]
else:
    print(result["action"])
```

---

### `coverage()` → `dict`

Returns active country prefixes allowed on this account.

```python
result = sms.coverage()
if result["result"] == "OK":
    print(result["prefixes"])  # → ["965", "966", "971", "973", "974"]
else:
    print(result["action"])    # ERR033 = no active coverage, contact kwtSMS
```

---

### `status(msg_id)` → `dict`

Get delivery status for a sent message. Uses the `/report/` endpoint.

```python
delivery = sms.status(result["msg-id"])
if delivery["result"] == "OK":
    print(delivery["status"])        # "DELIVERED", "FAILED", "PENDING", "REJECTED"
    print(delivery["delivered-at"])  # unix timestamp (GMT+3)
else:
    print(delivery["action"])
```

Returns OK or ERROR dict. Never raises. Common error codes: ERR019 (no reports yet), ERR020 (ID not found), ERR021 (not ready yet).

---

### `send_with_retry(mobile, message, sender=None, max_retries=3)` → `dict`

Send SMS with automatic ERR028 retry. ERR028 means "wait 15 seconds before resending to this number." This method sleeps 16 seconds and retries automatically, up to `max_retries` times (default 3, so up to 4 total calls).

```python
result = sms.send_with_retry("96598765432", "Your OTP is: 123456")
# if ERR028 occurs: waits 16s and retries, up to 3 times
```

Non-ERR028 errors are returned immediately without retry. Never raises.

---

### `parse_webhook(payload)` → `dict`

Parse a kwtSMS delivery receipt webhook payload. kwtSMS can POST delivery receipts to your server as JSON.

```python
from kwtsms import parse_webhook

# In your webhook endpoint (Flask/FastAPI/Django):
result = parse_webhook(request.json)
if result["ok"]:
    print(result["msg_id"])        # matches the msg-id from send()
    print(result["phone"])         # recipient number
    print(result["status"])        # "DELIVERED", "FAILED", "PENDING", "REJECTED"
    print(result["delivered_at"])  # unix timestamp, or None
else:
    print(result["error"])         # "Missing required field: 'msg-id'"
```

---

### AsyncKwtSMS

Async version of `KwtSMS` for use with `asyncio`. Requires the optional `aiohttp` dependency:

```bash
pip install kwtsms[async]
```

```python
from kwtsms import AsyncKwtSMS

sms = AsyncKwtSMS.from_env()

async def send_otp(phone: str, code: str):
    ok, balance, error = await sms.verify()
    result = await sms.send(phone, f"Your OTP is: {code}")
    delivery = await sms.status(result["msg-id"])
    return result
```

`AsyncKwtSMS` mirrors `KwtSMS` exactly: `verify()`, `balance()`, `send()`, `status()`, `from_env()`, `purchased` property. Maximum 200 numbers per `send()` call (no auto-batching in async mode). All methods return dicts and never raise.

---

## Utility functions

```python
from kwtsms import (normalize_phone, validate_phone_input, clean_message,
                     parse_webhook, find_country_code, validate_phone_format)

# Normalize a phone number: strips +, 00, spaces, dashes; converts Arabic digits;
# strips domestic trunk prefix (e.g. 9660559... becomes 966559...)
normalize_phone("+96598765432")      # → "96598765432"
normalize_phone("00 965 9876-5432") # → "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")     # → "96598765432"
normalize_phone("9660559123456")    # → "966559123456"  (Saudi trunk 0 stripped)

# Validate a phone number: returns (is_valid, error, normalized)
ok, error, number = validate_phone_input("+96598765432")
# → (True, None, "96598765432")

ok, error, number = validate_phone_input("user@gmail.com")
# → (False, "'user@gmail.com' is an email address, not a phone number", "")

ok, error, number = validate_phone_input("123")
# → (False, "'123' is too short to be a valid phone number (3 digits, minimum is 7)", "123")

ok, error, number = validate_phone_input("96512345678")
# → (False, "Invalid Kuwait mobile number: after +965 must start with 4, 5, 6, 9", "96512345678")

# Find country code from a normalized number
find_country_code("96598765432")    # → "965" (Kuwait)
find_country_code("12125551234")    # → "1"   (USA/Canada)
find_country_code("8887654321")     # → None  (unknown)

# Validate phone format against country-specific rules (length + mobile prefix)
valid, error = validate_phone_format("96598765432")   # → (True, None)
valid, error = validate_phone_format("96512345678")   # → (False, "Invalid Kuwait mobile...")

# Clean message text: also called automatically inside send()
clean_message("Your OTP is: ١٢٣٤٥٦ 🎉")  # → "Your OTP is: 123456 "
```

---

## Input sanitization

### Phone numbers

All phone numbers are normalized automatically before every API call:

1. Arabic/Hindi digits (`٠١٢٣٤٥٦٧٨٩` / `۰۱۲۳۴۵۶۷۸۹`) → Latin (`0123456789`)
2. All non-digit characters stripped (`+`, spaces, dashes, dots, brackets, etc.)
3. Leading zeros stripped (handles `00` country code prefix)
4. Domestic trunk prefix stripped after country code (e.g., `9660559...` → `966559...`)
5. Country-specific validation: checks local number length and mobile prefix for 80+ countries

Numbers must include the country code (e.g., `96598765432` for Kuwait, not `98765432`).

### Message text

`send()` calls `clean_message()` automatically before every API call. Three types of content cause silent delivery failure (API returns OK, message stuck in queue, credits wasted):

| Content | Effect | What happens |
|---------|--------|-------------|
| **Emojis** | Stuck in queue indefinitely, no error returned | Stripped automatically |
| **Hidden characters** (zero-width space, BOM, soft hyphen) | Spam filter rejection or queue stuck | Stripped automatically |
| **Arabic/Hindi digits** in body (`١٢٣٤`) | OTP codes may render inconsistently | Converted to Latin automatically |
| **HTML tags** | ERR027, message rejected | Stripped automatically |

Arabic **letters** are fully supported and are NOT stripped.

---

## CLI

For a standalone cross-platform CLI, see [kwtsms-cli](https://github.com/boxlinknet/kwtsms-cli).

---

## Error handling

Every API error response includes an `action` field with guidance. `send()` never raises: network failures are returned as a dict with `code="NETWORK"`.

```python
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
if result["result"] == "OK":
    save_to_db(msg_id=result["msg-id"], balance=result["balance-after"])
else:
    print(result["code"])        # e.g. "ERR010" or "NETWORK"
    print(result["description"]) # "Account balance is zero."
    print(result["action"])      # "Recharge credits at kwtsms.com."
```

Common error codes:

| Code | Meaning |
|------|---------|
| `ERR003` | Wrong username or password |
| `ERR006` | No valid phone numbers, missing country code |
| `ERR008` | Sender ID is banned or not found (case sensitive) |
| `ERR010` | Zero balance |
| `ERR011` | Insufficient balance |
| `ERR025` | Invalid phone number, missing country code |
| `ERR026` | Country not activated on this account |
| `ERR028` | Must wait 15s before sending to the same number again |

---

## Phone number formats

All formats are accepted. Numbers are normalized automatically:

| Input | Sent as |
|-------|---------|
| `+96598765432` | `96598765432` |
| `0096598765432` | `96598765432` |
| `965 9876 5432` | `96598765432` |
| `965-9876-5432` | `96598765432` |
| `٩٦٥٩٨٧٦٥٤٣٢` (Arabic digits) | `96598765432` |

Numbers must include the country code. `98765432` (local) will be rejected by the API. Use `96598765432`.

---

## Test mode

Set `KWTSMS_TEST_MODE=1` or `test_mode=True`. Messages are queued but **not delivered**, no credits consumed.

```python
sms = KwtSMS.from_env()   # KWTSMS_TEST_MODE=1 in .env
result = sms.send("96598765432", "Test message")
# Message is queued: visible in kwtsms.com → Account → Queue
# Delete it from the queue to recover credits
```

Set `KWTSMS_TEST_MODE=0` before going live.

---

## Sender ID

`KWT-SMS` is a shared sender for **testing only**. It can cause delays and is blocked on some Kuwait carriers. Register a private sender ID on [kwtsms.com](https://kwtsms.com) before going live.

**Sender IDs are case sensitive**: `Kuwait` is not the same as `KUWAIT` or `kuwait`.

| | Promotional | Transactional |
|--|-------------|---------------|
| **Use for** | Bulk SMS, marketing, offers | OTP, alerts, notifications |
| **Delivery to DND numbers** | Blocked, credits lost | Bypasses DND (whitelisted) |
| **Speed** | May have delays | Priority delivery |
| **Cost** | 10 KD one-time | 15 KD one-time |

**For OTP/authentication, you must use a Transactional sender ID.** Using Promotional for OTP means messages to DND numbers are silently blocked and credits are still deducted.

---

## Best practices

### Validate locally before calling the API

Don't send invalid data to the API. Validate first to avoid wasted API calls:

```python
from kwtsms import validate_phone_input, clean_message

# Check phone number before sending
ok, error, normalized = validate_phone_input(user_input)
if not ok:
    show_user_error(error)  # "Phone number is required", "'abc' is not a phone number", etc.
    return

# Check country is active (cache prefixes at startup)
if not any(normalized.startswith(p) for p in cached_prefixes):
    show_user_error("SMS delivery to this country is not available.")
    return

# Check message is not empty after cleaning
message = clean_message(user_input_message)
if not message.strip():
    show_user_error("Message is empty.")
    return

result = sms.send(normalized, message)  # only valid input reaches the API
```

### Save msg-id and balance-after from every send

```python
if result["result"] == "OK":
    db.save("sms_balance", result["balance-after"])   # track balance: no extra API call needed
    db.save_message(msg_id=result["msg-id"], ...)     # needed for status checks later
```

### OTP messages

- Always include your app/company name: `"Your OTP for APPNAME is: 123456"`
- Wait at least 3–4 minutes before allowing resend
- Generate a new code on each resend, and invalidate all previous codes
- Use a **Transactional** sender ID (not Promotional)
- Send to one number per request (avoid ERR028 in batches)

### User-facing error messages

Don't show raw API errors to end users:

| Situation | Show to user | Show to admin/logs |
|-----------|-------------|-------------------|
| Invalid phone | "Please enter a valid phone number with country code" | The actual validation error |
| Auth error (ERR003) | "SMS service temporarily unavailable" | Log the error + alert admin |
| No balance (ERR010/011) | "SMS service temporarily unavailable" | Alert admin to recharge |
| Rate limited (ERR028) | "Please wait before requesting another code" | Log the rate limit hit |

---

## Security checklist

Before going live, make sure:

- [ ] CAPTCHA enabled on all forms that trigger SMS (OTP, signup, password reset)
- [ ] Rate limit per phone number (max 3–5 requests/hour)
- [ ] Rate limit per IP address (max 10–20 requests/hour)
- [ ] Monitoring/alerting on failed sends and balance depletion
- [ ] Test mode OFF (`KWTSMS_TEST_MODE=0`)
- [ ] Private sender ID registered (not `KWT-SMS`)
- [ ] Transactional sender ID for OTP (not Promotional)
- [ ] Credentials in `.env` or env vars (not hardcoded)

---

## What's handled automatically

- Phone normalization (strips `+`, `00`, spaces, dashes; converts Arabic/Hindi digits)
- Input validation (catches emails, empty strings, too short/long, before the API is called)
- Message cleaning (strips emojis, hidden control characters, HTML tags; converts Arabic digits)
- API error enrichment (`action` field added to every error response)
- Bulk batching (auto-splits lists >200 numbers into batches of 200, 0.5s between batches)
- ERR013 backoff (queue full: retries 3× at 30s / 60s / 120s automatically)
- Balance caching (every send response includes `balance-after`, no extra API call needed)
- JSONL logging (one line per API call, password always masked, timestamps in UTC)

> **Note:** `unix-timestamp` in API responses is **GMT+3** (Asia/Kuwait server time), not UTC.
> Log `ts` fields written by this client are always UTC ISO-8601.

---

## Logging

One JSON line per API call written to `kwtsms.log` (or the path in `KWTSMS_LOG_FILE`). Password is always masked.

```json
{"ts":"2026-03-04T10:00:00+00:00","endpoint":"send","request":{"username":"python_username","password":"***","sender":"MYAPP","mobile":"96598765432","message":"Your OTP is: 123456","test":"0"},"response":{"result":"OK","msg-id":"f4c841ad...","numbers":1,"points-charged":1,"balance-after":149,"unix-timestamp":1741082400},"ok":true,"error":null}
```

> `ts` is always **UTC**. `unix-timestamp` inside `response` is **GMT+3** (Asia/Kuwait server time).

Set `log_file=""` or `KWTSMS_LOG_FILE=` to disable logging.

---

## FAQ

**1. My message was sent successfully (result: OK) but the recipient didn't receive it. What happened?**

Check the **Sending Queue** at [kwtsms.com](https://www.kwtsms.com/login/). If your message is stuck there, it was accepted by the API but not dispatched. Common causes are emoji in the message, hidden characters from copy-pasting, or spam filter triggers. Delete it from the queue to recover your credits. Also verify that `test` mode is off (`KWTSMS_TEST_MODE=0`). Test messages are queued but never delivered.

**2. What is the difference between Test mode and Live mode?**

**Test mode** (`KWTSMS_TEST_MODE=1`) sends your message to the kwtSMS queue but does NOT deliver it to the handset. No SMS credits are consumed. Use this during development. **Live mode** (`KWTSMS_TEST_MODE=0`) delivers the message for real and deducts credits. Always develop in test mode and switch to live only when ready for production.

**3. What is a Sender ID and why should I not use "KWT-SMS" in production?**

A **Sender ID** is the name that appears as the sender on the recipient's phone (e.g., "MY-APP" instead of a random number). `KWT-SMS` is a shared test sender. It causes delivery delays, is blocked on Virgin Kuwait, and should never be used in production. Register your own private Sender ID through your kwtSMS account. For OTP/authentication messages, you need a **Transactional** Sender ID to bypass DND (Do Not Disturb) filtering.

**4. I'm getting ERR003 "Authentication error". What's wrong?**

You are using the wrong credentials. The API requires your **API username and API password**, NOT your account mobile number. Log in to [kwtsms.com](https://www.kwtsms.com/login/), go to Account → API settings, and check your API credentials. Also make sure you are using POST (not GET) and `Content-Type: application/json`.

**5. Can I send to international numbers (outside Kuwait)?**

International sending is **disabled by default** on kwtSMS accounts. Contact kwtSMS support to request activation for specific country prefixes. Use `coverage()` to check which countries are currently active on your account. Be aware that activating international coverage increases exposure to automated abuse, so implement rate limiting and CAPTCHA before enabling.

---

## Help & Support

- **[kwtSMS FAQ](https://www.kwtsms.com/faq/)**: Answers to common questions about credits, sender IDs, OTP, and delivery
- **[kwtSMS Support](https://www.kwtsms.com/support.html)**: Open a support ticket or browse help articles
- **[Contact kwtSMS](https://www.kwtsms.com/#contact)**: Reach the kwtSMS team directly for Sender ID registration and account issues
- **[API Documentation (PDF)](https://www.kwtsms.com/doc/KwtSMS.com_API_Documentation_v41.pdf)**: kwtSMS REST API v4.1 full reference
- **[kwtSMS Dashboard](https://www.kwtsms.com/login/)**: Recharge credits, buy Sender IDs, view message logs, manage coverage
- **[Other Integrations](https://www.kwtsms.com/integrations.html)**: Plugins and integrations for other platforms and languages

---

## Repository layout

```
kwtsms_python/
├── src/kwtsms/
│   ├── _core.py      ← KwtSMS class + all sync logic
│   ├── _async.py     ← AsyncKwtSMS (requires kwtsms[async])
│   └── __init__.py   ← public exports
├── tests/            ← pytest test suite
├── examples/         ← runnable example scripts
├── pyproject.toml
├── uv.lock
├── README.md
└── LICENSE
```

---

## License

MIT
