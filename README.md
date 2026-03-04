# kwtsms Python

Official Python client for the [kwtSMS API](https://kwtsms.com) — Kuwait SMS gateway.

Send SMS, check balance, validate numbers, and manage SMS flows with zero external dependencies.

---

kwtSMS is a Kuwaiti SMS gateway trusted by top businesses to deliver messages anywhere in the world, with private Sender ID, free API testing, non-expiring credits, and competitive flat-rate pricing. Secure, simple to integrate, built to last.

Open a free account in under 1 minute — no paperwork or payment required. 🚀 [Click here to get started →](https://www.kwtsms.com/signup/)

---

## Install

```bash
pip install kwtsms
uv add kwtsms
poetry add kwtsms
pipenv install kwtsms
```

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
    test_mode=False,
    log_file="kwtsms.log",      # set to "" to disable
)

# Verify credentials
ok, balance, error = sms.verify()

# Send SMS
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
if result["result"] == "OK":
    msg_id  = result["msg-id"]         # save — needed for status/DLR lookups
    balance = result["balance-after"]  # save — no need to call balance() again
else:
    print(result["code"])        # e.g. "ERR003"
    print(result["description"]) # human-readable error
    print(result["action"])      # what to do — always present on errors

# Override sender ID per call
result = sms.send("96598765432", "Hello", sender="MY-APP")

# Send to multiple numbers — auto-batches >200
result = sms.send(["96598765432", "+96512345678", "0096511111111"], "Hello!")

# Invalid numbers are reported in result["invalid"], not raised
result = sms.send(["96598765432", "abc", "user@gmail.com"], "Hello")
# result["invalid"] → [{"input": "abc", "error": "..."}, {"input": "user@gmail.com", ...}]

# Bulk send (>200 numbers) — same call, batched automatically
result = sms.send(list_of_1000_numbers, "Hello!")
if result.get("bulk"):
    print(result["result"])         # "OK", "PARTIAL", or "ERROR"
    print(result["batches"])        # number of API calls made
    print(result["numbers"])        # total numbers accepted
    print(result["points-charged"]) # total credits used
    print(result["msg-ids"])        # one msg-id per batch
    print(result["errors"])         # per-batch errors if any

# Check balance
balance = sms.balance()  # also auto-updated after every successful send

# List sender IDs registered on this account
ids = sms.senderids()   # → ["KWT-SMS", "MY-APP"]

# List active country prefixes
result = sms.coverage() # → {"result": "OK", "prefixes": ["965", "966", ...]}

# Validate numbers before bulk send
report = sms.validate(["96598765432", "+96512345678", "abc", "123"])
# report["ok"]       → valid and routable
# report["er"]       → format error (API + locally rejected)
# report["nr"]       → no route for country
# report["rejected"] → pre-rejected with per-number error messages
# report["raw"]      → full raw API response
```

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

## CLI

A `kwtsms` command is installed automatically with the package:

```bash
kwtsms setup                                          # first-time wizard
kwtsms verify                                         # test credentials + show balance + purchased
kwtsms balance                                        # check available and purchased credits
kwtsms senderid                                       # list sender IDs on this account
kwtsms coverage                                       # list active country prefixes
kwtsms send 96598765432 "Your OTP is: 123456"        # send SMS
kwtsms send 96598765432,96512345678 "Hello!"          # multiple numbers (no spaces around commas)
kwtsms send "96598765432, 96512345678" "Hello!"       # or quote the list (spaces OK inside quotes)
kwtsms send 96598765432 "Hello" --sender MY-APP       # override sender ID
kwtsms send 96598765432 "Hello" --sender "kwt sms"   # sender ID with spaces — quote it
kwtsms validate 96598765432 +96512345678              # validate numbers
```

## Phone number formats

All formats are accepted — numbers are normalized automatically before every call:

| Input | Sent as |
|-------|---------|
| `+96598765432` | `96598765432` |
| `0096598765432` | `96598765432` |
| `965 9876 5432` | `96598765432` |
| `965-9876-5432` | `96598765432` |
| `٩٦٥٩٨٧٦٥٤٣٢` (Arabic digits) | `96598765432` |

## Utility functions

```python
from kwtsms import normalize_phone, validate_phone_input, clean_message

# Normalize a phone number
normalize_phone("+965 9876-5432")      # → "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")       # → "96598765432"

# Validate before sending — returns (is_valid, error, normalized)
ok, error, number = validate_phone_input("user@gmail.com")
# → (False, "'user@gmail.com' is an email address, not a phone number", "")

ok, error, number = validate_phone_input("+96598765432")
# → (True, None, "96598765432")

# Clean message text — also called automatically inside send()
clean_message("Your OTP is: ١٢٣٤٥٦ 🎉")  # → "Your OTP is: 123456 "
```

## Error handling

Every API error response includes an `action` field:

```python
try:
    result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")
except RuntimeError as e:
    # Network/HTTP failure
    print(f"Network error: {e}")
else:
    if result["result"] == "OK":
        save_to_db(msg_id=result["msg-id"], balance=result["balance-after"])
    else:
        print(result["code"])        # e.g. "ERR010"
        print(result["description"]) # "Account balance is zero."
        print(result["action"])      # "Top up your kwtSMS account at kwtsms.com."
```

## Test mode

Set `KWTSMS_TEST_MODE=1` to queue messages without delivering them — no credits consumed.
Messages appear in kwtsms.com → Account → Queue. Delete them to recover credits.
Switch to `KWTSMS_TEST_MODE=0` before going live.

## Sender ID

`KWT-SMS` is a shared sender for **testing only** — it can cause delays and is blocked on
some Kuwait carriers. Before going live, register a private sender ID on
[kwtsms.com](https://kwtsms.com). Use a **Transactional** sender ID for OTP messages
to ensure delivery to DND numbers.

## What's handled automatically

- Phone normalization (strips `+`, `00`, spaces, dashes; converts Arabic/Hindi digits)
- Input validation (catches emails, empty strings, too short/long — before the API is called)
- Message cleaning (strips emojis, hidden control characters, HTML tags; converts Arabic digits)
- API error enrichment (`action` field added to every error response)
- Bulk batching (auto-splits lists >200 numbers into batches of 200, 0.5s between batches)
- ERR013 backoff (queue full — retries 3× at 30s / 60s / 120s automatically)
- Balance caching (every send response includes `balance-after` — no extra API call needed)
- JSONL logging (one line per API call, password always masked, timestamps in UTC)

> **Note:** `unix-timestamp` in API responses is **GMT+3** (Asia/Kuwait server time), not UTC.
> Log `ts` fields written by this client are always UTC ISO-8601.

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
