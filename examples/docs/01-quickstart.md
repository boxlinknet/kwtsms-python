# Example 01: Quick Start

**File:** `examples/01-quickstart.py`
**Run:** `python examples/01-quickstart.py`

Verifies your credentials and sends your first SMS. Start here after setting
up your `.env` file.

---

## Flow

```
Start
  |
  +-- 1. Load client from .env  ------>  KwtSMS.from_env()
  |
  +-- 2. Verify credentials  --------->  sms.verify()
  |        |
  |        +-- FAIL: print error, exit  (wrong credentials / account blocked)
  |        +-- OK:   print balance, continue
  |
  +-- 3. Send a single SMS  ---------->  sms.send(phone, message)
  |        |
  |        +-- OK:    print msg-id, credits used, balance after
  |        +-- ERROR: print description and action hint
  |
  End
```

---

## Step-by-Step

### Step 1: Create the client

```python
from kwtsms import KwtSMS

sms = KwtSMS.from_env()
```

`from_env()` reads credentials in this order:

1. Environment variables already set in the process (Docker, CI, server config)
2. `.env` file in the current working directory

### Step 2: Verify credentials

```python
ok, balance, error = sms.verify()
```

Returns `(ok: bool, balance: float | None, error: str | None)`.

Call `verify()` at startup in production to detect:

| Error | Meaning |
|-------|---------|
| `ERR003` | Wrong API username or password |
| `ERR005` | Account is blocked |
| `ERR024` | Server IP not in the IP whitelist |

### Step 3: Send a single SMS

```python
result = sms.send("96598765432", "Hello from kwtSMS!")
```

Phone numbers are normalized automatically:

| Input | Normalized |
|-------|-----------|
| `+96598765432` | `96598765432` |
| `0096598765432` | `96598765432` |
| `٩٦٥٩٨٧٦٥٤٣٢` | `96598765432` |

**Success response fields:**

| Field | Description |
|-------|-------------|
| `msg-id` | Save this for delivery status lookups |
| `numbers` | Count of recipients accepted |
| `points-charged` | Credits consumed |
| `balance-after` | Remaining balance: save to avoid an extra `/balance/` call |

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ERR003` | Wrong API credentials | Use API username, not your phone number or website login |
| `ERR024` | IP lockdown active | Add server IP at kwtsms.com: Account: API: IP Lockdown |
| Message in queue, not delivered | Test mode on | Set `KWTSMS_TEST_MODE=0` in `.env` |
