# Example 04: Phone Number Validation

**File:** `examples/04-validation.py`
**Run:** `python examples/04-validation.py`

Validate and normalize phone numbers before sending: locally (instant, no
API call) or against the kwtSMS routing database (checks carrier support
and country activation on your account).

---

## Two Validation Modes

| Mode | Function | API call | Speed | What it checks |
|------|----------|----------|-------|----------------|
| Local | `validate_phone_input()` | No | Instant | Format, length, email detection |
| API | `sms.validate()` | Yes | Network | Format + carrier routing for your account |

---

## Step-by-Step

### Step 1: Local validation (no API call)

```python
from kwtsms._core import validate_phone_input

valid, error, normalized = validate_phone_input("+965 9876 5432")
# -> (True, None, "96598765432")

valid, error, normalized = validate_phone_input("user@example.com")
# -> (False, "'user@example.com' is an email address, not a phone number", "")
```

`validate_phone_input()` returns `(is_valid: bool, error: str | None, normalized: str)`.

**What it catches:**

| Input | Error |
|-------|-------|
| `""` | Phone number is required |
| `"user@example.com"` | Email address, not a phone number |
| `"abc"` | Not a valid phone number, no digits found |
| `"123"` | Too short (3 digits, minimum is 7) |
| `"1234567890123456"` | Too long (16 digits, maximum is 15) |

### Step 2: Normalization

```python
from kwtsms._core import normalize_phone

normalize_phone("+965 9876-5432")  # -> "96598765432"
normalize_phone("0096598765432")   # -> "96598765432"
normalize_phone("٩٦٥٩٨٧٦٥٤٣٢")   # -> "96598765432"  (Arabic-Indic digits)
normalize_phone("۹۶۵۹۸۷۶۵۴۳۲")   # -> "96598765432"  (Extended Arabic-Indic)
```

Normalization steps (applied in order):

1. Arabic-Indic and Extended Arabic-Indic digits converted to Latin (0-9)
2. All non-digit characters stripped (spaces, `+`, `-`, `.`, `(`, `)`, etc.)
3. Leading zeros stripped (handles `00` country code prefix)

### Step 3: API validation (carrier routing check)

```python
from kwtsms import KwtSMS

sms = KwtSMS.from_env()
report = sms.validate(["96598765432", "+44 20 7946 0958", "abc"])
```

`validate()` runs local validation on every number first. Numbers that fail
locally are collected in `report["rejected"]` without making an API call.
Numbers that pass locally are sent to the kwtSMS `/validate/` endpoint.

**Report fields:**

```python
{
    "ok":       ["96598765432"],   # valid and routable
    "er":       ["abc"],           # format error
    "nr":       ["447946095800"],  # no route (country not activated)
    "raw":      {...},             # full API response, or None if no API call
    "error":    None,              # set if the entire API call failed
    "rejected": [                  # numbers rejected before API call
        {"input": "abc", "error": "'abc' is not a valid phone number, no digits found"}
    ],
}
```

---

## Use Cases

### Clean a CSV before a campaign

```python
import csv
from kwtsms._core import validate_phone_input

valid_numbers = []
with open("contacts.csv") as f:
    for row in csv.DictReader(f):
        ok, err, normalized = validate_phone_input(row["phone"])
        if ok:
            valid_numbers.append(normalized)
        else:
            print(f"Skipping {row['phone']!r}: {err}")
```

### Validate user input on a sign-up form

```python
def register_phone(raw_phone: str) -> dict:
    valid, error, normalized = validate_phone_input(raw_phone)
    if not valid:
        return {"ok": False, "error": "Please enter a valid phone number."}
    # Save normalized phone to database
    return {"ok": True, "phone": normalized}
```

### Check country routing before sending

```python
report = sms.validate(["96598765432", "971504496677"])  # Kuwait + UAE
if "971504496677" in report["nr"]:
    print("UAE not activated. Contact kwtSMS support.")
```
