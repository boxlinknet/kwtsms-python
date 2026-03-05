# kwtSMS Python: Examples

Step-by-step examples covering everything from a first send to a production
OTP system with CAPTCHA, rate limiting, and brute-force protection.

---

## Setup

### 1. Install

```bash
pip install kwtsms
# or with uv:
uv add kwtsms
```

Requires Python 3.8+, no external dependencies.

### 2. Configure `.env`

```bash
cp examples/.env.example .env
```

```ini
KWTSMS_USERNAME=your_api_username   # API user, NOT your phone number or website login
KWTSMS_PASSWORD=your_api_password
KWTSMS_SENDER_ID=KWT-SMS            # Replace with a private Sender ID before production
KWTSMS_TEST_MODE=1                  # Set to 0 when ready to deliver real messages
KWTSMS_LOG_FILE=kwtsms.log          # Leave empty to disable request logging
```

Credentials: kwtsms.com: Account: API.

### 3. Verify

```bash
python examples/01-quickstart.py
```

Expected output: `Connected! Balance: X credits`

---

## Examples

| # | File | What it covers | Docs |
|---|------|---------------|------|
| 01 | `01-quickstart.py` | Verify credentials, send your first SMS | [docs](docs/01-quickstart.md) |
| 02 | `02-otp.py` | Generate and send a one-time code (basic) | [docs](docs/02-otp.md) |
| 03 | `03-bulk.py` | Send to many numbers, auto-batching for >200 | [docs](docs/03-bulk.md) |
| 04 | `04-validation.py` | Local phone validation and API routing check | [docs](docs/04-validation.md) |
| 05 | `05-error-handling.py` | Handle every error category with the right action | [docs](docs/05-error-handling.md) |
| 06 | `06-message-cleaning.py` | What `clean_message()` strips and why | [docs](docs/06-message-cleaning.md) |
| 07 | `07-django.py` | Service class, view, management command | [docs](docs/07-django.md) |
| 08 | `08-flask.py` | Flask blueprint, OTP endpoints, health check | [docs](docs/08-flask.md) |
| 09 | `09-fastapi.py` | FastAPI router, Pydantic models, Depends injection | [docs](docs/09-fastapi.md) |
| 10 | `10-otp-production.py` | Full production OTP: SQLite, CAPTCHA, rate limiting, brute-force | [docs](docs/10-otp-production.md) |

---

## Reference

- [Phone number formats](docs/reference.md#phone-number-format-reference): accepted, normalized, and rejected inputs
- [Sender ID guide](docs/reference.md#sender-id): Promotional vs Transactional, DND, registration
- [Error codes ERR001–ERR033](docs/reference.md#error-code-reference): descriptions and recommended actions
- [Pre-launch checklist](docs/reference.md#pre-launch-checklist): credentials, security, content, anti-abuse

---

## CLI

Send SMS and verify credentials from the terminal:

```bash
# Verify credentials and check balance
kwtsms verify

# Send a message
kwtsms send 96598765432 "Hello from kwtSMS"

# Override sender ID for one message
kwtsms send 96598765432 "Hello" --sender MY-BRAND
```

Reads credentials from `.env` or environment variables.
