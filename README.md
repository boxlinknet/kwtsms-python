# kwtsms Python

Official Python client for the [kwtSMS API](https://kwtsms.com) — Kuwait SMS gateway.

Send SMS, check balance, validate numbers, and manage SMS flows with zero external dependencies.

---

## Install

```bash
pip install kwtsms
```

Works with any Python package manager:

```bash
uv add kwtsms       # uv
poetry add kwtsms   # poetry
pipenv install kwtsms  # pipenv
```

## Quick start

```python
from kwtsms import KwtSMS

sms = KwtSMS.from_env()

# Verify credentials
ok, balance, error = sms.verify()

# Send SMS
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
if result["result"] == "OK":
    msg_id  = result["msg-id"]
    balance = result["balance-after"]   # no need to call balance() again
else:
    print(result["code"])        # e.g. "ERR003"
    print(result["description"]) # human-readable error
    print(result["action"])      # what to do — e.g. "Check KWTSMS_USERNAME..."

# Override sender ID per call
result = sms.send("96598765432", "Hello", sender="MY-APP")

# Send to multiple numbers (auto-batches >200)
result = sms.send(["96598765432", "+96512345678"], "Hello!")

# Invalid numbers are reported, not raised
result = sms.send(["96598765432", "abc", "user@gmail.com"], "Hello")
# result["invalid"] → [{"input": "abc", "error": "..."}, {"input": "user@gmail.com", ...}]

# Check balance
balance = sms.balance()

# Validate numbers before bulk send
report = sms.validate(["96598765432", "+96512345678", "123"])
# report["ok"]       → valid and routable
# report["er"]       → format error (API) + locally rejected
# report["nr"]       → no route for country
# report["rejected"] → pre-rejected with per-number error messages
```

## Configuration

Create a `.env` file in your project root:

```ini
KWTSMS_USERNAME=your_api_user
KWTSMS_PASSWORD=your_api_pass
KWTSMS_SENDER_ID=YOUR-SENDERID   # KWT-SMS for testing only
KWTSMS_TEST_MODE=1                # 1 = test (safe default), 0 = live
KWTSMS_LOG_FILE=kwtsms.log
```

Or set the same keys as environment variables. `from_env()` checks env vars first, then the `.env` file.

First time? Run the setup wizard:

```bash
kwtsms setup
```

## CLI

A `kwtsms` command is installed automatically with the package:

```bash
kwtsms setup                                     # first-time wizard
kwtsms verify                                    # test credentials
kwtsms balance                                   # check balance
kwtsms send 96598765432 "Your OTP is: 123456"   # send SMS
kwtsms validate 96598765432 +96512345678         # validate numbers
```

## Phone number formats

All formats are accepted — numbers are normalized automatically before every call:

| Input | Sent as |
|-------|---------|
| `+96598765432` | `96598765432` |
| `0096598765432` | `96598765432` |
| `965 9876 5432` | `96598765432` |
| `٩٦٥٩٨٧٦٥٤٣٢` (Arabic digits) | `96598765432` |

## Test mode

Set `KWTSMS_TEST_MODE=1` to queue messages without delivering them. No credits consumed.
Switch to `0` before going live.

## Sender ID

`KWT-SMS` is a shared sender for **testing only** — it can cause delays and is blocked on
some Kuwait carriers. Before going live, register a private sender ID on
[kwtsms.com](https://kwtsms.com). Use a **Transactional** sender ID for OTP messages
to ensure delivery to DND numbers.

## Utility functions

```python
from kwtsms import normalize_phone, validate_phone_input, clean_message

# Normalize a phone number to digits-only international format
normalize_phone("+965 9876-5432")   # → "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")    # → "96598765432"

# Validate before sending — returns (is_valid, error, normalized)
ok, error, number = validate_phone_input("user@gmail.com")
# → (False, "'user@gmail.com' is an email address, not a phone number", "")

ok, error, number = validate_phone_input("+96598765432")
# → (True, None, "96598765432")

# Clean message text (also called automatically inside send())
clean_message("Your OTP is: ١٢٣٤٥٦ 🎉")  # → "Your OTP is: 123456 "
```

## What's handled automatically

- Phone normalization (strips `+`, `00`, spaces, dashes; converts Arabic/Hindi digits)
- Input validation (catches emails, empty strings, too short/long before hitting the API)
- Message cleaning (strips emojis, hidden control characters, HTML tags)
- API error enrichment (`action` field added to every error response)
- Bulk batching (auto-splits lists >200 numbers into batches of 200)
- Balance caching (every send response includes `balance-after` — no extra API call needed)
- JSONL logging (one line per API call, password always masked)

## Repository layout

```
kwtsms_python/
├── kwtsms/          ← installable package (published to PyPI)
│   ├── src/kwtsms/
│   │   ├── _core.py     ← KwtSMS class + all logic
│   │   ├── _cli.py      ← kwtsms CLI command
│   │   └── __init__.py  ← public exports
│   └── tests/
└── docs/            ← design docs, implementation plan, publish workflow
```

## Links

- PyPI: https://pypi.org/project/kwtsms
- [kwtSMS API Documentation](https://www.kwtsms.com/doc/KwtSMS.com_API_Documentation_v41.pdf) — kwtSMS API v4.1 (PDF)
- [kwtSMS FAQ](https://kwtsms.com/faq/) — answers to common questions about credits, sender IDs, OTP, and delivery
- [kwtSMS Support](https://kwtsms.com/support.html) — open a support ticket or browse help articles
- [Contact kwtSMS](https://kwtsms.com/#contact) — reach the kwtSMS team directly for sender ID registration and account issues

## License

MIT
