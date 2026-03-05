"""
Example 01: Quick Start
-----------------------
The fastest path to sending your first SMS with kwtSMS.

Requirements:
    pip install kwtsms
    .env file with KWTSMS_USERNAME and KWTSMS_PASSWORD

Run:
    python examples/01-quickstart.py
"""

from kwtsms import KwtSMS

# ── Step 1: Create the client ────────────────────────────────────────────────
#
# KwtSMS.from_env() loads credentials from environment variables or a .env file.
# Required: KWTSMS_USERNAME, KWTSMS_PASSWORD
# Optional: KWTSMS_SENDER_ID, KWTSMS_TEST_MODE, KWTSMS_LOG_FILE
#
# Your .env file should look like this:
#
#   KWTSMS_USERNAME=your_api_username
#   KWTSMS_PASSWORD=your_api_password
#   KWTSMS_SENDER_ID=MY-BRAND
#   KWTSMS_TEST_MODE=1           # set to 0 when going live
#   KWTSMS_LOG_FILE=kwtsms.log

sms = KwtSMS.from_env()

# ── Step 2: Verify your credentials ─────────────────────────────────────────
#
# Always verify before going live. Returns your current balance.

ok, balance, error = sms.verify()

if not ok:
    print(f"Connection failed: {error}")
    raise SystemExit(1)

print(f"Connected! Balance: {balance} credits\n")

# ── Step 3: Send a single SMS ────────────────────────────────────────────────
#
# Numbers are normalized automatically:
#   "+965 9876-5432"  -> "96598765432"
#   "0096598765432"   -> "96598765432"
#   "٩٦٥٩٨٧٦٥٤٣٢"    -> "96598765432"  (Arabic digits)

result = sms.send("96598765432", "Hello from kwtSMS! Your first message is working.")

if result["result"] == "OK":
    print("SMS sent successfully!")
    print(f"  Message ID   : {result['msg-id']}")
    print(f"  Credits used : {result['points-charged']}")
    print(f"  Balance after: {result['balance-after']}")
else:
    print(f"Failed to send: {result['description']}")
    print(f"  Action: {result.get('action', 'See error code for details')}")
