# Example 10: Production OTP Flow

**File:** `examples/10-otp-production.py`
**Run:** `python examples/10-otp-production.py`

Complete reference implementation for production OTP delivery. Drop this
into any Python web application. Covers all production requirements without
any external dependencies beyond the standard library and `kwtsms`.

---

## Requirements Covered

| Requirement | Implementation |
|-------------|---------------|
| Phone validation | `validate_phone_input()` before any API call |
| CAPTCHA | `verify_captcha()` stub (Turnstile / hCaptcha) |
| Rate limiting | Per-phone and per-IP, configurable window |
| Secure storage | HMAC-SHA256 hash of code, never plaintext |
| OTP expiry | Configurable TTL (default: 5 minutes) |
| Brute-force protection | Max 5 attempts, code deleted on lockout |
| Safe error messages | Internal errors logged, user sees generic message |
| Audit trail | `msg-id` and `balance-after` saved per send |
| SQLite storage | Included, zero external dependencies |

---

## Quick-Start Checklist

1. Register a **Transactional** Sender ID on kwtsms.com.
   OTP to DND numbers is silently blocked on Promotional IDs.
   kwtsms.com: Buy SenderID: Transactional (~15 KD, up to 5 working days)

2. Set environment variables:
   ```bash
   KWTSMS_USERNAME=your_api_username
   KWTSMS_PASSWORD=your_api_password
   KWTSMS_SENDER_ID=YOUR-TRANSACTIONAL-ID
   KWTSMS_TEST_MODE=0    # must be 0 in production
   APP_SECRET=<output of: python -c "import secrets; print(secrets.token_hex(32))">
   ```

3. Set `KWTSMS_TEST_MODE=0` before going live.

---

## Architecture

```
send_otp(phone, captcha_token, remote_ip)
  |
  +-- 1. validate_phone_input(phone)  -- local, no API call
  |        FAIL -> "Please enter a valid phone number with country code."
  |
  +-- 2. verify_captcha(token, ip)
  |        FAIL -> "CAPTCHA verification failed. Please try again."
  |
  +-- 3. _is_rate_limited(phone, ip)
  |        FAIL -> "Too many requests. Try again in N minutes."
  |
  +-- 4. Generate code, hash with HMAC-SHA256, store in SQLite
  |
  +-- 5. sms.send(phone, message)
  |        FAIL -> delete stored code, log full error, return user-safe message
  |        OK   -> save msg-id to DB, log send event for rate limiting
  |
  +-- return (True, "Verification code sent.")

verify_otp(phone, code)
  |
  +-- lookup by phone in DB
  |        NOT FOUND -> "No verification code found. Request a new one."
  |
  +-- check expiry
  |        EXPIRED -> delete, "Code expired. Request a new one."
  |
  +-- check attempts >= MAX_ATTEMPTS
  |        LOCKED  -> delete, "Too many incorrect attempts. Request a new code."
  |
  +-- hmac.compare_digest(expected_hash, stored_hash)
  |        WRONG -> increment attempts, "Incorrect code. N attempt(s) remaining."
  |        OK    -> delete code, return (True, "Phone number verified successfully.")
```

---

## Security Details

### OTP Hashing

Codes are stored as HMAC-SHA256 hashes, never in plaintext:

```python
def _hash_otp(phone: str, code: str) -> str:
    message = f"{phone}:{code}".encode()
    return hmac.new(APP_SECRET.encode(), message, hashlib.sha256).hexdigest()
```

The phone number is included in the hash to prevent cross-account substitution
attacks (a code generated for phone A cannot be used to verify phone B).

### Constant-Time Comparison

```python
hmac.compare_digest(expected, stored)
```

Prevents timing attacks where an attacker measures response time to guess
partial code values.

### Rate Limiting

```python
RATE_LIMIT  = 3    # max sends per phone per window
RATE_WINDOW = 600  # 10 minutes
```

Both per-phone and per-IP limits are enforced. The IP limit is 3x the
per-phone limit to allow shared IPs (NAT, corporate networks).

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_SECRET` | (required) | HMAC key for OTP hashing. Generate with `secrets.token_hex(32)` |
| `OTP_DB_PATH` | `otp_store.db` | SQLite database file path |
| `OTP_TTL` | `300` | OTP expiry in seconds (5 minutes) |
| `OTP_RATE_LIMIT` | `3` | Max sends per phone per window |
| `OTP_RATE_WINDOW` | `600` | Rate limit window in seconds (10 minutes) |
| `OTP_MAX_ATTEMPTS` | `5` | Max incorrect verify attempts before lockout |

---

## CAPTCHA Integration

Replace the stub in `verify_captcha()` with a real provider:

### Cloudflare Turnstile

```python
import urllib.request, urllib.parse, json, os

def verify_captcha(token, remote_ip=None):
    resp = urllib.request.urlopen(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        urllib.parse.urlencode({
            "secret":   os.environ["TURNSTILE_SECRET"],
            "response": token,
            "remoteip": remote_ip or "",
        }).encode()
    )
    data = json.loads(resp.read())
    return data["success"], "" if data["success"] else "CAPTCHA failed"
```

Add the Turnstile widget to your HTML form using the site key from
Cloudflare: Zero Trust: Turnstile.

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Users on DND never receive OTP | Promotional sender ID | Register Transactional ID |
| `app.logger.error` missing | Not in a web framework context | Use `logging.error()` |
| SQLite locked error | High concurrency | Switch to PostgreSQL or Redis |
| Rate limit blocks legitimate users | `RATE_WINDOW` too short | Increase `OTP_RATE_WINDOW` |
