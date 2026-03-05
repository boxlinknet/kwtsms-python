"""
Example 03: Bulk Send
----------------------
Send to many numbers. Lists with more than 200 numbers are split into
batches of 200 automatically. A 0.5-second delay is added between batches
to stay within the kwtSMS safe rate limit.

Run:
    python examples/03-bulk.py
"""

from kwtsms import KwtSMS

sms = KwtSMS.from_env()

# ── Small list (≤ 200 numbers): single API request ────────────────────────────
#
# Any list with 200 or fewer valid numbers is sent in a single /send/ call.

small_list = [
    "96598765432",
    "96512345678",
    "+965 9876 1111",     # normalized automatically: 96598761111
    "0096598762222",      # normalized automatically: 96598762222
    "٩٦٥٩٨٧٦٣٣٣٣",      # Arabic digits, normalized to: 96598763333
]

print("Sending to small list...")
result = sms.send(small_list, "Hello from kwtSMS bulk send!")

if result["result"] == "OK":
    print(f"  Sent to      : {result['numbers']} number(s)")
    print(f"  Message ID   : {result['msg-id']}")
    print(f"  Credits used : {result['points-charged']}")
    print(f"  Balance after: {result['balance-after']}")
else:
    print(f"  Failed: {result['description']}")
    print(f"  Action: {result.get('action', '')}")

# Show any numbers that were skipped due to invalid format
if "invalid" in result:
    print(f"\n  Skipped {len(result['invalid'])} invalid number(s):")
    for entry in result["invalid"]:
        print(f"    {entry['input']!r}: {entry['error']}")

# ── Large list (> 200 numbers): auto-batching ─────────────────────────────────
#
# send() detects > 200 valid numbers and calls _send_bulk() automatically.
# The result dict has a different shape: result["bulk"] is True.

print("\n\nSending to large list (auto-batch)...")

large_list = [f"9659{str(i).zfill(7)}" for i in range(350)]

result = sms.send(large_list, "Bulk campaign message from kwtSMS.")

print(f"  Bulk mode    : {result.get('bulk', False)}")
print(f"  Batches sent : {result.get('batches', 1)}")
print(f"  Total sent   : {result.get('numbers', 0)} number(s)")
print(f"  Credits used : {result.get('points-charged', 0)}")
print(f"  Balance after: {result.get('balance-after')}")
print(f"  Message IDs  : {result.get('msg-ids', [])}")

if result["result"] == "OK":
    print("  All batches delivered successfully.")
elif result["result"] == "PARTIAL":
    print(f"\n  PARTIAL: {len(result['errors'])} batch(es) failed:")
    for err in result["errors"]:
        print(f"    Batch {err['batch']}: [{err['code']}] {err['description']}")
elif result["result"] == "ERROR":
    print(f"\n  All batches failed:")
    for err in result.get("errors", []):
        print(f"    Batch {err['batch']}: [{err['code']}] {err['description']}")
