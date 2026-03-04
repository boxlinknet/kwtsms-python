# kwtsms Python

Official Python client for the [kwtSMS API](https://kwtsms.com) — Kuwait SMS gateway.

Send SMS, check balance, validate numbers, and manage OTP flows with zero external dependencies.

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

# Send SMS
result = sms.send("96598765432", "Your OTP for MYAPP is: 123456")

# Override sender ID per call
result = sms.send("96598765432", "Hello", sender="MY-APP")

# Send to multiple numbers (auto-batches >200)
result = sms.send(["96598765432", "+96512345678"], "Hello!")

# Check balance
balance = sms.balance()

# Verify credentials
ok, balance, error = sms.verify()

# Validate numbers before bulk send
report = sms.validate(["96598765432", "+96512345678", "123"])
# report["ok"] → valid, report["er"] → format error, report["nr"] → no route
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

## What's handled automatically

- Phone normalization (strips `+`, `00`, spaces, dashes; converts Arabic/Hindi digits)
- Message cleaning (strips emojis, hidden control characters, HTML tags)
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
- [kwtSMS FAQ](https://kwtsms.com/faq) — answers to common questions about credits, sender IDs, OTP, and delivery
- [kwtSMS Support](https://kwtsms.com/support.html) — open a support ticket or browse help articles
- [Contact kwtSMS](https://kwtsms.com/#contact) — reach the kwtSMS team directly for sender ID registration and account issues

## License

MIT
