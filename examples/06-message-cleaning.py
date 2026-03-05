"""
Example 06: Message Cleaning
------------------------------
Demonstrates the automatic message sanitization that runs on every send().

Why this matters:
    Messages with emojis, hidden Unicode characters, or HTML tags get stuck
    in the kwtSMS queue and are never delivered, but credits ARE consumed.
    The clean_message() function prevents this silently on every send() call.

You do not need to call this manually. send() does it for you.
This example is for educational purposes and manual pre-flight checks.

Run:
    python examples/06-message-cleaning.py
"""

from kwtsms._core import clean_message

examples = {
    # Emojis (cause silent queue lock)
    "Hello! 👋 Your order is ready 📦":     "Hello!  Your order is ready ",
    "Flash sale 🔥 50% off today only!":    "Flash sale  50% off today only!",
    "Meeting confirmed ✅":                  "Meeting confirmed ",

    # Keycap emojis (1️⃣ 2️⃣ etc.) — U+20E3 combining enclosing keycap
    "Step 1️⃣ open the app":                 "Step 1 open the app",

    # Flag emojis (regional indicators: 🇰🇼 🇺🇸)
    "Shipping to 🇰🇼 Kuwait":               "Shipping to  Kuwait",

    # HTML (causes ERR027 from the API)
    "<b>Important:</b> Your account is <i>active</i>.":
        "Important: Your account is active.",
    "<p>Click <a href='#'>here</a> to confirm.</p>":
        "Click here to confirm.",

    # Arabic/Persian digits converted to Latin
    "رصيدك: ٢٥٠ دينار":                    "رصيدك: 250 دينار",
    "كود التحقق: ١٢٣٤٥٦":                  "كود التحقق: 123456",
    "کد تأیید: ۱۲۳۴۵۶":                    "کد تأیید: 123456",  # Persian digits

    # Zero-width spaces (from copy-pasting from Word or WhatsApp)
    "Hello\u200BWorld":                     "HelloWorld",
    "Clean\uFEFFText":                      "CleanText",   # BOM character

    # Soft hyphens (invisible, from PDF copy-paste)
    "Hyphen\u00ADate":                      "Hyphenate",

    # Arabic text preserved perfectly
    "مرحباً بكم في خدمة الرسائل النصية":   "مرحباً بكم في خدمة الرسائل النصية",
    "عزيزي العميل، طلبك جاهز للاستلام":    "عزيزي العميل، طلبك جاهز للاستلام",

    # Newlines and tabs preserved (SMS supports them)
    "Line 1\nLine 2\nLine 3":               "Line 1\nLine 2\nLine 3",
    "Column1\tColumn2":                     "Column1\tColumn2",

    # Mixed: emoji + Arabic + hidden chars
    "طلبك 📦 رقم ١٢٣\u200B جاهز!":         "طلبك  رقم 123 جاهز!",
}

print("=== MESSAGE CLEANING EXAMPLES ===\n")

passed = 0
failed = 0

for input_text, expected in examples.items():
    output = clean_message(input_text)
    ok = output == expected
    if ok:
        passed += 1
    else:
        failed += 1

    status = "OK " if ok else "ERR"
    print(f"{status}  Input   : {input_text!r}")
    if not ok:
        print(f"     Expected: {expected!r}")
        print(f"     Got     : {output!r}")
    else:
        print(f"     Output  : {output!r}")
    print()

print("-" * 50)
print(f"Passed: {passed} / {len(examples)}")
if failed:
    print(f"Failed: {failed}")

# ── Edge case: emoji-only message ─────────────────────────────────────────────
#
# clean_message() returns "" for a message that is entirely emojis or invisible
# characters. send() catches this and returns ERR009 locally before any API call.

print("\n=== EDGE CASE: emoji-only message ===\n")

emoji_only = "👋 🎉 🔥 🚀"
cleaned = clean_message(emoji_only)
print(f"Input  : {emoji_only!r}")
print(f"Cleaned: {cleaned!r}")
print(f"Empty? : {not cleaned}")
print()
print("send() catches this and returns ERR009 without hitting the API:")
print("  {\"result\": \"ERROR\", \"code\": \"ERR009\", \"description\": \"Message is empty after cleaning...\"}")
