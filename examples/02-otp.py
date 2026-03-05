"""
Example 02: One-Time Password (OTP)
------------------------------------
Generate and send a 6-digit OTP. Shows in-memory storage with expiry.

For a full production implementation with database storage, rate limiting,
CAPTCHA, and brute-force protection, see examples/09-otp-production.py.

Run:
    python examples/02-otp.py
"""

import secrets
import time
from kwtsms import KwtSMS

# ── Step 1: Configure the client ─────────────────────────────────────────────
#
# For OTP delivery, use a TRANSACTIONAL sender ID.
# Promotional sender IDs (like the default KWT-SMS) cannot deliver to DND numbers.
# Register one at kwtsms.com -> Buy SenderID -> Transactional

sms = KwtSMS.from_env()

# ── Step 2: Generate a secure OTP ────────────────────────────────────────────
#
# secrets.randbelow() is cryptographically secure. Never use random.randint().

def generate_otp(length: int = 6) -> str:
    """Generate a zero-padded numeric OTP of the given length."""
    upper = 10 ** length
    return str(secrets.randbelow(upper)).zfill(length)


# ── Step 3: Store the OTP temporarily ────────────────────────────────────────
#
# In production, store in a database with the phone number as the key.
# See examples/09-otp-production.py for a production-ready implementation.

OTP_TTL = 300  # seconds (5 minutes)

_otp_store: dict = {}


def store_otp(phone: str, code: str) -> None:
    """Store OTP with expiry timestamp."""
    _otp_store[phone] = {
        "code":    code,
        "expires": time.time() + OTP_TTL,
    }


def verify_otp(phone: str, code: str) -> tuple:
    """
    Verify an OTP.
    Returns (ok: bool, reason: str).
    """
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


# ── Step 4: Send the OTP ─────────────────────────────────────────────────────

phone  = "96598765432"
code   = generate_otp()
appname = "MyApp"

result = sms.send(phone, f"Your {appname} verification code is: {code}. Valid for 5 minutes.")

if result["result"] == "OK":
    store_otp(phone, code)
    print(f"OTP sent to {phone}")
    print(f"  Message ID   : {result['msg-id']}")
    print(f"  Credits used : {result['points-charged']}")
else:
    print(f"Failed to send OTP: {result['description']}")
    print(f"  Action: {result.get('action', 'See error code for details')}")
    raise SystemExit(1)

# ── Step 5: Verify the OTP (simulate user input) ─────────────────────────────
#
# In production, the user submits the code via a web form or API endpoint.
# This just demonstrates correct and incorrect verification.

print("\n-- Simulating verification --")

ok, reason = verify_otp(phone, "000000")  # wrong code
print(f"Wrong code  : ok={ok}, reason={reason!r}")

ok, reason = verify_otp(phone, code)       # correct code
print(f"Correct code: ok={ok}, reason={reason!r}")

ok, reason = verify_otp(phone, code)       # already used (deleted after first success)
print(f"Reused code : ok={ok}, reason={reason!r}")
