# Example 02: One-Time Password (OTP)

**File:** `examples/02-otp.py`
**Run:** `python examples/02-otp.py`

Generate a cryptographically secure 6-digit OTP, send it via kwtSMS, and
verify it. Uses in-memory storage. For a production implementation with
database storage, rate limiting, CAPTCHA, and brute-force protection, see
`examples/09-otp-production.py`.

---

## Flow

```
User requests OTP
  |
  +-- generate_otp()  ----------->  secrets.randbelow(1_000_000)
  |
  +-- sms.send(phone, message)  ->  kwtSMS API
  |        |
  |        +-- OK:    store_otp(phone, code)
  |        +-- ERROR: return error to caller
  |
User submits code
  |
  +-- verify_otp(phone, code)
         |
         +-- Not found: "No OTP found. Request a new one."
         +-- Expired:   "OTP has expired. Request a new one."
         +-- Wrong:     "Incorrect OTP. Try again."
         +-- Correct:   delete code, return True
```

---

## Step-by-Step

### Step 1: Use a transactional sender ID

```python
sms = KwtSMS.from_env()
```

OTP delivery requires a **Transactional sender ID**. Promotional sender IDs
(like the default `KWT-SMS`) cannot deliver to DND numbers. DND is extremely
common in Kuwait. Register a Transactional ID at kwtsms.com: Buy SenderID:
Transactional.

Set `KWTSMS_SENDER_ID=YOUR-TRANSACTIONAL-ID` in `.env`.

### Step 2: Generate a secure OTP

```python
import secrets

def generate_otp(length: int = 6) -> str:
    upper = 10 ** length
    return str(secrets.randbelow(upper)).zfill(length)
```

Always use `secrets.randbelow()`. Never use `random.randint()` for security
codes: `random` is not cryptographically secure.

### Step 3: Send the OTP

```python
result = sms.send(phone, f"Your MyApp code is: {code}. Valid for 5 minutes.")
```

Best practices for the message text:

- Include the app name so users recognize the message
- State the expiry time
- Never say "Do not share with anyone" (this is expected and not useful)
- Keep it under 160 characters to stay within one SMS credit

### Step 4: Store and verify

```python
def store_otp(phone: str, code: str) -> None:
    _otp_store[phone] = {"code": code, "expires": time.time() + 300}

def verify_otp(phone: str, code: str) -> tuple:
    entry = _otp_store.get(phone)
    if not entry:
        return False, "No OTP found. Request a new one."
    if time.time() > entry["expires"]:
        del _otp_store[phone]
        return False, "OTP has expired. Request a new one."
    if entry["code"] != code:
        return False, "Incorrect OTP. Try again."
    del _otp_store[phone]
    return True, "Verified"
```

Delete the code immediately after successful verification (one-time use).

---

## Security Notes

| Requirement | Implementation |
|-------------|----------------|
| Cryptographically secure generation | `secrets.randbelow()`, not `random` |
| Expiry | 5-minute TTL, enforced on every verification attempt |
| One-time use | Delete code immediately after success |
| Brute-force protection | See `examples/09-otp-production.py` |
| Plaintext storage | See `examples/09-otp-production.py` for HMAC hashing |

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| User receives code but DND shows as delivered in kwtsms.com | Transactional ID missing | Register one at kwtsms.com: Buy SenderID: Transactional |
| Code works in test but not in production | `KWTSMS_TEST_MODE=1` left on | Set `KWTSMS_TEST_MODE=0` in `.env` |
| `ERR009` before API call | Message was emoji-only | Use plain text in OTP messages |
