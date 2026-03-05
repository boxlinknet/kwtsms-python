"""
Example 05: Error Handling
---------------------------
Handle every error category correctly. Each category has a different
recommended action: some need a code fix, some need account config, some
need a retry.

Run:
    python examples/05-error-handling.py
"""

from kwtsms import KwtSMS

sms = KwtSMS.from_env()


# ── Error response structure ──────────────────────────────────────────────────
#
# Every error response from send(), verify(), validate(), and balance() is a
# dict with these fields:
#
#   result      : "ERROR"
#   code        : "ERR003", "ERR010", "NETWORK", "ERR_INVALID_INPUT", etc.
#   description : Human-readable description from the API
#   action      : Developer-friendly guidance added by this client
#
# OK responses never have a "code" field.

def handle_result(result: dict, context: str = "") -> None:
    """Print a result dict with helpful formatting."""
    if context:
        print(f"\n-- {context} --")

    if result["result"] == "OK":
        print(f"  OK: msg-id={result.get('msg-id')} credits={result.get('points-charged')}")
        return

    code = result.get("code", "UNKNOWN")
    desc = result.get("description", "")
    action = result.get("action", "")

    print(f"  ERROR [{code}]: {desc}")
    if action:
        print(f"  Action: {action}")


# ── Category 1: Invalid input (caught locally, no API call) ──────────────────

print("=== Category 1: Invalid input ===")

# Empty phone number
handle_result(sms.send("", "Test"), "Empty phone number")

# Email instead of phone
handle_result(sms.send("user@example.com", "Test"), "Email as phone")

# Too short
handle_result(sms.send("123", "Test"), "Too short (3 digits)")

# Non-numeric
handle_result(sms.send("not-a-number", "Test"), "Non-numeric input")

# Emoji-only message (caught locally, returns ERR009 without API call)
handle_result(sms.send("96598765432", "👋🏼"), "Emoji-only message")


# ── Category 2: Authentication errors ────────────────────────────────────────
#
# Wrong credentials: fix KWTSMS_USERNAME / KWTSMS_PASSWORD in .env.
# Account blocked: contact kwtSMS support.
# IP lockdown: add server IP at kwtsms.com -> Account -> API -> IP Lockdown.

print("\n=== Category 2: Authentication errors ===")

bad_client = KwtSMS(
    username="wrong_user",
    password="wrong_pass",
    sender_id="KWT-SMS",
    test_mode=True,
    log_file="",
)
ok, balance, error = bad_client.verify()
print(f"\n  verify() with wrong credentials: ok={ok}")
if not ok:
    print(f"  Error: {error}")


# ── Category 3: Sender ID errors ─────────────────────────────────────────────
#
# ERR008: Sender ID not registered on this account or is banned.
# Fix: register the sender ID at kwtsms.com -> Sender IDs.
# Note: Sender IDs are case-sensitive.

print("\n=== Category 3: Sender ID errors ===")

unregistered_client = KwtSMS(
    username=sms.username,
    password=sms.password,
    sender_id="ZZNOTREAL",
    test_mode=True,
    log_file="",
)
handle_result(
    unregistered_client.send("96598765432", "Test"),
    "Unregistered sender ID",
)


# ── Category 4: Balance errors ────────────────────────────────────────────────
#
# ERR010: Zero balance. Recharge credits at kwtsms.com.
# ERR011: Insufficient balance for this batch. Buy more credits.

print("\n=== Category 4: Balance errors (simulated code, not real API call) ===")

balance_error = {
    "result": "ERROR",
    "code": "ERR010",
    "description": "Your account balance is zero",
    "action": "Recharge credits at kwtsms.com.",
}
handle_result(balance_error, "Zero balance")


# ── Category 5: Network errors ────────────────────────────────────────────────
#
# NETWORK: No internet, DNS failure, timeout, firewall block.
# send() never raises. Network errors are returned as a dict with code="NETWORK".

print("\n=== Category 5: Network errors (simulated) ===")

network_error = {
    "result": "ERROR",
    "code": "NETWORK",
    "description": "Network error: [Errno -2] Name or service not known",
    "action": "Check your internet connection and try again.",
}
handle_result(network_error, "Network failure")


# ── Full error handling pattern ───────────────────────────────────────────────
#
# This is the recommended pattern for production code.

print("\n=== Recommended production error handling ===\n")

ERROR_ACTIONS = {
    # Permanent errors: fix code/config
    "ERR003": "check_credentials",
    "ERR005": "contact_support",
    "ERR008": "check_sender_id",
    "ERR_INVALID_INPUT": "fix_phone_numbers",

    # Transient errors: retry
    "ERR013": "retry_with_backoff",   # queue full (handled automatically in bulk mode)
    "ERR028": "wait_15_seconds",      # too fast

    # Balance errors: recharge
    "ERR010": "recharge_credits",
    "ERR011": "recharge_credits",

    # Network errors: retry
    "NETWORK": "retry_or_check_connectivity",
}

result = sms.send("96598765432", "Production test message")

if result["result"] == "OK":
    # Save msg-id for delivery status lookup
    msg_id = result["msg-id"]
    balance_after = result["balance-after"]
    print(f"Success: msg_id={msg_id}, balance_after={balance_after}")

elif result["result"] == "ERROR":
    code = result.get("code", "UNKNOWN")
    action_key = ERROR_ACTIONS.get(code, "check_docs")

    print(f"Error [{code}]: {result.get('description')}")
    print(f"Action: {result.get('action')}")
    print(f"Handler: {action_key}")

    # Never expose raw error codes to end users. Show a safe message.
    user_message = "We couldn't send your message. Please try again."
    print(f"User-facing message: {user_message!r}")
