"""
Example 09: Production OTP Flow
---------------------------------
Complete reference implementation for production OTP delivery.

Covers every production requirement:
    - Phone format validation (local, before any API call)
    - CAPTCHA verification hook (Cloudflare Turnstile or hCaptcha)
    - Rate limiting per phone and per IP
    - Secure OTP storage (HMAC-SHA256, never plaintext)
    - OTP expiry (5 minutes, configurable)
    - Brute-force protection (5 max attempts per code)
    - User-safe error messages (no raw API codes exposed)
    - msg-id and balance-after saved from every send response
    - SQLite storage with optional Redis adapter

+==============================================================+
|                   QUICK-START CHECKLIST                      |
+==============================================================+
|  1. Register a TRANSACTIONAL Sender ID on kwtsms.com         |
|     OTP to DND numbers is silently blocked on Promotional    |
|     IDs. kwtsms.com -> Buy SenderID -> Transactional         |
|     (~15 KD, up to 5 working days)                           |
|  2. Set env vars: KWTSMS_USERNAME, KWTSMS_PASSWORD,          |
|     KWTSMS_SENDER_ID                                         |
|  3. Generate APP_SECRET: python -c "import secrets;         |
|     print(secrets.token_hex(32))"                           |
|  4. Set KWTSMS_TEST_MODE=0 before going live                  |
+==============================================================+

SENDER ID MATTERS:
    Promotional sender IDs (KWT-SMS, your brand) CANNOT deliver to DND
    numbers. DND is extremely common in Kuwait. If you use a Promotional ID
    for OTP, many users will silently never receive their code.
    Register a Transactional ID for OTP.

Run:
    python examples/09-otp-production.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from typing import Optional, Tuple

from kwtsms import KwtSMS
from kwtsms._core import validate_phone_input


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Load from environment. In production, set these as server environment variables.
# Never hardcode credentials.
APP_SECRET   = os.environ.get("APP_SECRET", "change-this-to-a-random-secret-in-production")
DB_PATH      = os.environ.get("OTP_DB_PATH", "otp_store.db")
OTP_TTL      = int(os.environ.get("OTP_TTL", "300"))       # seconds (5 minutes)
RATE_LIMIT   = int(os.environ.get("OTP_RATE_LIMIT", "3"))  # max sends per phone per window
RATE_WINDOW  = int(os.environ.get("OTP_RATE_WINDOW", "600"))  # rate window in seconds
MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))  # max verify attempts per code


# ─────────────────────────────────────────────────────────────────────────────
# Database setup (SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_db() -> None:
    """Create OTP tables if they do not exist."""
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                phone       TEXT    NOT NULL,
                code_hash   TEXT    NOT NULL,
                created_at  INTEGER NOT NULL,
                expires_at  INTEGER NOT NULL,
                attempts    INTEGER NOT NULL DEFAULT 0,
                msg_id      TEXT,
                used        INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (phone)
            );

            CREATE TABLE IF NOT EXISTS otp_send_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                phone       TEXT    NOT NULL,
                ip          TEXT,
                sent_at     INTEGER NOT NULL
            );
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Secure OTP storage helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hash_otp(phone: str, code: str) -> str:
    """
    Hash the OTP with HMAC-SHA256 using phone as salt and APP_SECRET as key.
    Stored in the DB instead of the plaintext code.
    """
    message = f"{phone}:{code}".encode()
    return hmac.new(APP_SECRET.encode(), message, hashlib.sha256).hexdigest()


def _verify_hash(phone: str, code: str, stored_hash: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    expected = _hash_otp(phone, code)
    return hmac.compare_digest(expected, stored_hash)


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting
# ─────────────────────────────────────────────────────────────────────────────

def _is_rate_limited(phone: str, ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if this phone or IP has exceeded the send rate limit.
    Returns (limited: bool, reason: str).
    """
    now = int(time.time())
    window_start = now - RATE_WINDOW

    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM otp_send_log WHERE phone=? AND sent_at > ?",
            (phone, window_start)
        ).fetchone()
        if row["cnt"] >= RATE_LIMIT:
            return True, f"Too many requests for this number. Try again in {RATE_WINDOW // 60} minutes."

        if ip:
            row = db.execute(
                "SELECT COUNT(*) as cnt FROM otp_send_log WHERE ip=? AND sent_at > ?",
                (ip, window_start)
            ).fetchone()
            if row["cnt"] >= RATE_LIMIT * 3:  # IP limit is 3x the per-phone limit
                return True, "Too many requests from this IP address. Try again later."

    return False, ""


def _log_send(phone: str, ip: Optional[str] = None) -> None:
    """Record an OTP send event for rate limiting."""
    with get_db() as db:
        db.execute(
            "INSERT INTO otp_send_log (phone, ip, sent_at) VALUES (?, ?, ?)",
            (phone, ip, int(time.time()))
        )


# ─────────────────────────────────────────────────────────────────────────────
# CAPTCHA verification hook
# ─────────────────────────────────────────────────────────────────────────────

def verify_captcha(token: str, remote_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Verify a CAPTCHA token before allowing an OTP send.

    Replace this stub with a real Cloudflare Turnstile or hCaptcha call:

    Cloudflare Turnstile:
        import urllib.request, urllib.parse, json
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

    hCaptcha:
        resp = urllib.request.urlopen(
            "https://hcaptcha.com/siteverify",
            urllib.parse.urlencode({
                "secret":   os.environ["HCAPTCHA_SECRET"],
                "response": token,
                "remoteip": remote_ip or "",
            }).encode()
        )
        data = json.loads(resp.read())
        return data["success"], "" if data["success"] else "CAPTCHA failed"
    """
    # Stub: always pass. Replace with a real implementation above.
    if not token:
        return False, "CAPTCHA token is required"
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# OTP API
# ─────────────────────────────────────────────────────────────────────────────

_sms: Optional[KwtSMS] = None


def _get_sms() -> KwtSMS:
    """Get or create the KwtSMS singleton."""
    global _sms
    if _sms is None:
        _sms = KwtSMS.from_env()
    return _sms


def send_otp(
    phone: str,
    captcha_token: str,
    remote_ip: Optional[str] = None,
    app_name: str = "MyApp",
) -> Tuple[bool, str]:
    """
    Send an OTP to a phone number.

    Returns (ok: bool, message: str).
    The message is always safe to show to the user.

    Steps:
        1. Validate phone format (local, instant)
        2. Verify CAPTCHA
        3. Check rate limit
        4. Generate OTP, hash it, store in DB
        5. Send via kwtSMS
        6. If send fails, roll back DB entry
    """
    # Step 1: Validate phone locally (no API call)
    valid, error, normalized = validate_phone_input(phone)
    if not valid:
        return False, "Please enter a valid phone number with country code."

    # Step 2: Verify CAPTCHA
    captcha_ok, captcha_err = verify_captcha(captcha_token, remote_ip)
    if not captcha_ok:
        return False, "CAPTCHA verification failed. Please try again."

    # Step 3: Rate limit check
    limited, limit_reason = _is_rate_limited(normalized, remote_ip)
    if limited:
        return False, limit_reason

    # Step 4: Generate and store OTP
    code = str(secrets.randbelow(1_000_000)).zfill(6)
    code_hash = _hash_otp(normalized, code)
    now = int(time.time())

    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO otp_codes
               (phone, code_hash, created_at, expires_at, attempts, msg_id, used)
               VALUES (?, ?, ?, ?, 0, NULL, 0)""",
            (normalized, code_hash, now, now + OTP_TTL)
        )

    # Step 5: Send via kwtSMS
    message = f"Your {app_name} verification code is: {code}. Valid for 5 minutes. Do not share it."
    result = _get_sms().send(normalized, message)

    if result["result"] != "OK":
        # Step 6: Roll back: delete the stored OTP so it is not orphaned
        with get_db() as db:
            db.execute("DELETE FROM otp_codes WHERE phone=?", (normalized,))
        # Log full error server-side, never expose to user
        print(f"[OTP] Send failed for {normalized}: [{result.get('code')}] {result.get('description')}")
        return False, "We could not send your verification code. Please try again."

    # Save msg-id and record the send event
    msg_id = result.get("msg-id")
    balance_after = result.get("balance-after")
    print(f"[OTP] Sent to {normalized}: msg_id={msg_id} balance_after={balance_after}")

    with get_db() as db:
        db.execute("UPDATE otp_codes SET msg_id=? WHERE phone=?", (msg_id, normalized))

    _log_send(normalized, remote_ip)

    return True, "Verification code sent."


def verify_otp(phone: str, code: str) -> Tuple[bool, str]:
    """
    Verify an OTP submitted by the user.

    Returns (ok: bool, message: str).

    Security properties:
        - Codes are stored as HMAC-SHA256 hashes, never plaintext
        - Constant-time comparison prevents timing attacks
        - Max 5 attempts per code, then the code is invalidated
        - Expired codes are rejected and cleaned up
        - Successfully used codes are deleted immediately
    """
    valid, _, normalized = validate_phone_input(phone)
    if not valid:
        return False, "Invalid phone number."

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM otp_codes WHERE phone=? AND used=0",
            (normalized,)
        ).fetchone()

        if not row:
            return False, "No verification code found. Request a new one."

        now = int(time.time())
        if now > row["expires_at"]:
            db.execute("DELETE FROM otp_codes WHERE phone=?", (normalized,))
            return False, "Verification code has expired. Request a new one."

        if row["attempts"] >= MAX_ATTEMPTS:
            db.execute("DELETE FROM otp_codes WHERE phone=?", (normalized,))
            return False, "Too many incorrect attempts. Request a new code."

        if not _verify_hash(normalized, code, row["code_hash"]):
            db.execute(
                "UPDATE otp_codes SET attempts=attempts+1 WHERE phone=?",
                (normalized,)
            )
            remaining = MAX_ATTEMPTS - row["attempts"] - 1
            if remaining > 0:
                return False, f"Incorrect code. {remaining} attempt(s) remaining."
            else:
                db.execute("DELETE FROM otp_codes WHERE phone=?", (normalized,))
                return False, "Too many incorrect attempts. Request a new code."

        # Code is correct: mark as used and delete
        db.execute("DELETE FROM otp_codes WHERE phone=?", (normalized,))

    return True, "Phone number verified successfully."


# ─────────────────────────────────────────────────────────────────────────────
# Demo run
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    setup_db()
    print("Production OTP demo\n")

    phone = "96598765432"
    captcha = "demo-token"
    ip = "203.0.113.1"

    # Send OTP
    print(f"Sending OTP to {phone}...")
    ok, msg = send_otp(phone, captcha, remote_ip=ip)
    print(f"  ok={ok}, message={msg!r}")

    if not ok:
        raise SystemExit(1)

    # Simulate brute-force
    print("\nSimulating brute-force (5 wrong attempts):")
    for attempt in range(1, 7):
        ok2, msg2 = verify_otp(phone, "000000")
        print(f"  attempt {attempt}: ok={ok2}, message={msg2!r}")
        if ok2 or "new code" in msg2.lower():
            break

    # Rate limiting demo
    print("\nRate limiting (send 4 times with same phone):")
    for i in range(4):
        ok3, msg3 = send_otp(phone, captcha, remote_ip=ip)
        print(f"  send {i+1}: ok={ok3}, message={msg3!r}")

    # Clean up demo DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("\nDemo DB cleaned up.")
