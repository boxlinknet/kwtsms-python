# kwtsms Python

Official Python client for the [kwtSMS API](https://kwtsms.com), the Kuwait SMS gateway.

Send SMS, check balance, validate numbers, and manage SMS flows with zero external dependencies. Python 3.8+.

---

## About kwtSMS

kwtSMS is a Kuwaiti SMS gateway trusted by top businesses to deliver messages anywhere in the world, with private Sender ID, free API testing, non-expiring credits, and competitive flat-rate pricing. Secure, simple to integrate, built to last.

Open a free account in under 1 minute. No paperwork or payment required.

[🚀 Click here to get started →](https://www.kwtsms.com/signup/)

---

## Prerequisites

You need **Python 3.8 or newer** and **pip** installed.

```bash
python3 --version   # check Python
pip --version        # check pip
```

If Python is not installed: download from https://www.python.org/downloads/

---

## Install

```bash
pip install kwtsms
```

Other package managers:

```bash
uv add kwtsms
poetry add kwtsms
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

## Configuration

Create a `.env` file in your project root:

```ini
KWTSMS_USERNAME=your_api_user
KWTSMS_PASSWORD=your_api_pass
KWTSMS_SENDER_ID=YOUR-SENDERID   # KWT-SMS for testing only
KWTSMS_TEST_MODE=1                # 1 = test (safe default), 0 = live
KWTSMS_LOG_FILE=kwtsms.log        # set to "" to disable logging
```

`from_env()` checks environment variables first, then the `.env` file.

First time? Run the setup wizard:

```bash
kwtsms setup
```

---

## Credential Management

**Never hardcode credentials.** They must be changeable without modifying code.

```python
# Option 1: Environment variables / .env file (recommended)
sms = KwtSMS.from_env()

# Option 2: Constructor (for custom config systems)
sms = KwtSMS(
    username="your_api_user",
    password="your_api_pass",
    sender_id="YOUR-SENDERID",
    test_mode=False,
    log_file="kwtsms.log",      # "" to disable
)
```

**For web apps:** Provide an admin settings page for updating credentials without touching code. Include a "Test Connection" button that calls `verify()`.

**For production:** Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) and pass credentials to the constructor.

---

## All methods

```python
sms = KwtSMS.from_env()

# Verify credentials: returns (ok, balance, error), never raises
ok, balance, error = sms.verify()

# Send SMS: single, multiple, or bulk (>200 auto-batched)
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
result = sms.send(["96598765432", "+96512345678"], "Hello!")
result = sms.send("96598765432", "Hello", sender="MY-APP")  # override sender

# Check balance, also auto-updated after every successful send
balance = sms.balance()

# Validate numbers before bulk send
report = sms.validate(["96598765432", "+96512345678", "abc"])

# List sender IDs registered on this account
result = sms.senderids()  # {"result": "OK", "senderids": ["KWT-SMS", "MY-APP"]}

# List active country prefixes
result = sms.coverage()   # {"result": "OK", "prefixes": ["965", "966", ...]}
```

**Send OK response:**
```python
{"result": "OK", "msg-id": "f4c841ad...", "numbers": 1, "points-charged": 1, "balance-after": 149, "unix-timestamp": 1741000800}
```

**Send ERROR response:**
```python
{"result": "ERROR", "code": "ERR003", "description": "Authentication error...", "action": "Wrong API username or password..."}
```

**Mixed valid/invalid input:** invalid numbers reported in `result["invalid"]`, valid numbers still sent.

**Bulk send (>200 numbers):** same `send()` call, auto-batched. Returns `result["bulk"] = True` with aggregated `msg-ids`, `batches`, `points-charged`.

---

## Utility functions

```python
from kwtsms import normalize_phone, validate_phone_input, clean_message

normalize_phone("+965 9876-5432")      # → "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")       # → "96598765432"

ok, error, number = validate_phone_input("user@gmail.com")
# → (False, "'user@gmail.com' is an email address, not a phone number", "")

clean_message("Your OTP is: ١٢٣٤٥٦ 🎉")  # → "Your OTP is: 123456 "
```

---

## Input sanitization

### Phone numbers

Normalized automatically before every API call: Arabic/Hindi digits converted, all non-digit characters stripped, leading zeros stripped. Numbers must include the country code (e.g., `96598765432` for Kuwait, not `98765432`).

### Message text

`send()` calls `clean_message()` automatically. Content that causes silent delivery failure:

| Content | Effect | Handled |
|---------|--------|---------|
| **Emojis** | Stuck in queue, no error, credits wasted | Stripped automatically |
| **Hidden characters** (BOM, zero-width space, soft hyphen) | Spam filter or queue stuck | Stripped automatically |
| **Arabic/Hindi digits** (`١٢٣٤`) | OTP codes render inconsistently | Converted to Latin |
| **HTML tags** | ERR027, message rejected | Stripped automatically |

Arabic **letters** are fully supported and NOT stripped.

---

## CLI

```bash
kwtsms setup                                          # first-time wizard
kwtsms verify                                         # test credentials + show balance + purchased
kwtsms balance                                        # check available and purchased credits
kwtsms senderid                                       # list sender IDs on this account
kwtsms coverage                                       # list active country prefixes
kwtsms send 96598765432 "Your OTP is: 123456"        # send SMS
kwtsms send 96598765432,96512345678 "Hello!"          # multiple numbers
kwtsms send 96598765432 "Hello" --sender "MY APP"    # override sender ID
kwtsms validate 96598765432 +96512345678              # validate numbers
```

---

## Error handling

Every API error response includes an `action` field:

```python
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
if result["result"] != "OK":
    print(result["code"])        # e.g. "ERR010"
    print(result["description"]) # "Account balance is zero."
    print(result["action"])      # "Recharge credits at kwtsms.com."
```

| Code | Meaning |
|------|---------|
| `ERR003` | Wrong username or password |
| `ERR006` | No valid phone numbers, missing country code |
| `ERR008` | Sender ID banned or not found (case sensitive) |
| `ERR010` | Zero balance |
| `ERR025` | Invalid phone number, missing country code |
| `ERR026` | Country not activated on this account |
| `ERR028` | Must wait 15s before sending to the same number again |

---

## Phone number formats

| Input | Sent as |
|-------|---------|
| `+96598765432` | `96598765432` |
| `0096598765432` | `96598765432` |
| `965 9876 5432` | `96598765432` |
| `965-9876-5432` | `96598765432` |
| `٩٦٥٩٨٧٦٥٤٣٢` (Arabic digits) | `96598765432` |

Numbers must include the country code. `98765432` (local) will be rejected. Use `96598765432`.

---

## Test mode

Set `KWTSMS_TEST_MODE=1` to queue messages without delivering them. No credits consumed.
Messages appear in kwtsms.com → Account → Queue. Delete them to recover credits.
Switch to `KWTSMS_TEST_MODE=0` before going live.

---

## Sender ID

`KWT-SMS` is a shared sender for **testing only**. It can cause delays and is blocked on some Kuwait carriers. Before going live, register a private sender ID on [kwtsms.com](https://kwtsms.com).

**Sender IDs are case sensitive**: `Kuwait` is not the same as `KUWAIT` or `kuwait`.

| | Promotional | Transactional |
|--|-------------|---------------|
| **Use for** | Bulk SMS, marketing, offers | OTP, alerts, notifications |
| **Delivery to DND numbers** | Blocked, credits lost | Bypasses DND (whitelisted) |
| **Speed** | May have delays | Priority delivery |
| **Cost** | 10 KD one-time | 15 KD one-time |

**For OTP, you must use Transactional**. Promotional sender IDs are silently blocked for DND subscribers and credits are still deducted.

---

## Best practices

- **Validate locally before calling the API**: check phone format, country coverage, message length before sending
- **Cache `coverage()` at startup**: reject unsupported countries locally instead of wasting an API call
- **Save `msg-id` and `balance-after`** from every send response: you need msg-id for status lookups, and balance-after eliminates extra API calls
- **OTP messages:** include app name, 3–4 min resend timer, new code on resend, Transactional sender ID
- **Don't show raw API errors to end users**: show friendly messages ("Please wait before requesting another code") and log the real error for admins

---

## Security checklist

Before going live:

- [ ] CAPTCHA on all SMS-triggering forms
- [ ] Rate limit per phone (max 3–5/hour)
- [ ] Rate limit per IP (max 10–20/hour)
- [ ] Monitoring on failed sends and balance depletion
- [ ] Test mode OFF (`KWTSMS_TEST_MODE=0`)
- [ ] Private sender ID (not `KWT-SMS`)
- [ ] Transactional sender ID for OTP
- [ ] Credentials not hardcoded

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

---

## FAQ

**1. Message sent OK but recipient didn't receive it?**

Check the **Sending Queue** at [kwtsms.com](https://www.kwtsms.com/login/). If stuck there: emoji, hidden characters, or spam filter. Delete from queue to recover credits. Also check `KWTSMS_TEST_MODE=0`.

**2. Test mode vs Live mode?**

Test mode queues but does NOT deliver. No credits consumed. Switch to `KWTSMS_TEST_MODE=0` for production.

**3. Why not use "KWT-SMS" in production?**

Shared test sender, delays, blocked on Virgin Kuwait. Register your own private Sender ID. Use Transactional for OTP.

**4. ERR003 "Authentication error"?**

Wrong credentials. Use your **API username/password** (not your account mobile number). Check at kwtsms.com → Account → API.

**5. Can I send internationally?**

Disabled by default. Contact kwtSMS support. Use `coverage()` to check active countries. Implement rate limiting before enabling.

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
├── kwtsms/          ← installable package (published to PyPI)
│   ├── src/kwtsms/
│   │   ├── _core.py     ← KwtSMS class + all logic
│   │   ├── _cli.py      ← kwtsms CLI command
│   │   └── __init__.py  ← public exports
│   └── tests/
└── docs/            ← design docs, PRD, publish workflow
```

---

## License

MIT
