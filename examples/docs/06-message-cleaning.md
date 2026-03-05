# Example 06: Message Cleaning

**File:** `examples/06-message-cleaning.py`
**Run:** `python examples/06-message-cleaning.py`

`clean_message()` runs automatically on every `send()` call. You do not
need to call it manually. This example explains what it strips and why.

---

## Why Message Cleaning Matters

| Problem | Symptom | Credits |
|---------|---------|---------|
| Emoji in message | Message stuck in queue, never delivered | Consumed |
| HTML tags | API returns ERR027 | Not consumed |
| Zero-width space | Delivery may fail silently | Consumed |
| Arabic-Indic digits (٢٥٠) | Some carriers cannot render them | Consumed |

`clean_message()` prevents all of these silently on every `send()` call.

---

## What Gets Stripped

### Emojis (all ranges)

```python
clean_message("Hello 👋 World")    # -> "Hello  World"
clean_message("Flash sale 🔥")     # -> "Flash sale "
clean_message("Shipping to 🇰🇼")   # -> "Shipping to "  (flag emoji)
clean_message("Step 1️⃣ open app")   # -> "Step 1 open app"  (keycap)
```

Emoji ranges covered:

| Range | Examples |
|-------|---------|
| U+1F600–U+1F64F | Emoticons (😀 😂 🤔) |
| U+1F300–U+1F5FF | Misc symbols and pictographs (🌍 🎁 🔑) |
| U+1F680–U+1F6FF | Transport and map (🚀 🚗 ✈️) |
| U+1F900–U+1FAFF | Supplemental and extended (🧠 🦾 🪄) |
| U+2600–U+26FF | Miscellaneous symbols (☀️ ⭐ ⚡) |
| U+2700–U+27BF | Dingbats (✂️ ✉️ ✅) |
| U+1F1E0–U+1F1FF | Regional indicators (flag emoji 🇰🇼 🇺🇸) |
| U+20E3 | Combining enclosing keycap (1️⃣ 2️⃣) |
| U+E0000–U+E007F | Tags block (subdivision flags 🏴󠁧󠁢󠁥󠁮󠁧󠁿) |
| U+1F000–U+1F0FF | Mahjong tiles and playing cards (🀄 🃏) |

### HTML tags

```python
clean_message("<b>Hello</b>")                # -> "Hello"
clean_message("<p>Click <a href='#'>here</a></p>")  # -> "Click here"
```

HTML is not supported by SMS. The API returns ERR027 if any tags are present.

### Arabic-Indic and Persian digits

```python
clean_message("كودك: ١٢٣٤٥٦")     # -> "كودك: 123456"
clean_message("کد شما: ۱۲۳۴۵۶")   # -> "کد شما: 123456"
```

Arabic text is fully preserved. Only the digits are converted.

### Hidden characters

| Character | Code point | Source |
|-----------|-----------|--------|
| Zero-width space | U+200B | Copy-paste from WhatsApp, Word |
| BOM | U+FEFF | Copy-paste from Windows editors |
| Soft hyphen | U+00AD | Copy-paste from PDF |
| Zero-width joiner | U+200D | Emoji sequences |
| Word joiner | U+2060 | Various text editors |

---

## What Is Preserved

| Content | Preserved | Notes |
|---------|-----------|-------|
| Arabic letters | Yes | Fully supported by kwtSMS |
| Persian/Farsi letters | Yes | Fully supported |
| Newlines (`\n`) | Yes | SMS supports line breaks |
| Tabs (`\t`) | Yes | SMS supports tabs |
| Latin text | Yes | Standard SMS charset |
| Numbers | Yes | Arabic-Indic converted to Latin |

---

## Emoji-Only Messages

If the entire message is stripped to empty, `send()` returns ERR009 locally
without making an API call:

```python
result = sms.send("96598765432", "👋 🎉 🔥")
# {
#     "result":      "ERROR",
#     "code":        "ERR009",
#     "description": "Message is empty after cleaning...",
#     "action":      "Message is empty. Provide a non-empty message text.",
# }
```

---

## Manual Pre-flight Check

```python
from kwtsms._core import clean_message

original = "Flash sale 🔥 50% off!"
cleaned  = clean_message(original)

print(f"Original : {original!r}")
print(f"Cleaned  : {cleaned!r}")
print(f"Safe?    : {bool(cleaned)}")
```
