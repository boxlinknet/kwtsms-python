# Example 03: Bulk Send

**File:** `examples/03-bulk.py`
**Run:** `python examples/03-bulk.py`

Send to many numbers. `send()` handles batching automatically: lists of 200
or fewer numbers are sent in a single API call; larger lists are split into
batches of 200 with a 0.5-second delay between each batch.

---

## Routing Logic

```
send(numbers, message)
  |
  +-- validate all numbers locally
  |        |
  |        +-- invalid: collected in result["invalid"]
  |        +-- valid:   proceed
  |
  +-- len(valid) <= 200?
  |        YES: single /send/ request
  |        NO:  _send_bulk() (batches of 200, 0.5s delay)
  |
  +-- return result dict
```

---

## Result Shapes

### Small list (≤ 200 valid numbers)

```python
result = sms.send(["96598765432", "96512345678"], "Hello!")
```

The result is the raw API response:

```python
{
    "result":          "OK",
    "msg-id":          "abc123",
    "numbers":         2,
    "points-charged":  2,
    "balance-after":   198,
    "unix-timestamp":  1700000000,
    # Present if any numbers were skipped:
    "invalid": [{"input": "bad", "error": "..."}],
}
```

### Large list (> 200 valid numbers)

```python
result = sms.send(numbers_350, "Hello!")
```

The result is an aggregated bulk summary:

```python
{
    "result":          "OK",       # "OK", "PARTIAL", or "ERROR"
    "bulk":            True,
    "batches":         2,
    "numbers":         350,
    "points-charged":  350,
    "balance-after":   150,
    "msg-ids":         ["abc123", "def456"],
    "errors":          [],
}
```

**PARTIAL** means at least one batch succeeded and at least one failed:

```python
if result["result"] == "PARTIAL":
    print(f"Partial success: {len(result['msg-ids'])} batches OK")
    for err in result["errors"]:
        print(f"  Batch {err['batch']}: [{err['code']}] {err['description']}")
```

---

## Step-by-Step

### Step 1: Build your number list

```python
# From a CSV file
import csv
with open("contacts.csv") as f:
    reader = csv.DictReader(f)
    numbers = [row["phone"] for row in reader]

# From a database
# numbers = [row.phone for row in Contact.objects.all()]
```

Numbers are normalized automatically. You can mix formats:

```python
numbers = [
    "+965 9876 5432",      # -> 96598765432
    "0096512345678",       # -> 96512345678
    "٩٦٥٩٨٧٦٥٤٣٢",        # Arabic digits -> 96598765432
]
```

### Step 2: Send with a single call

```python
result = sms.send(numbers, "Your message here")
```

`send()` validates each number locally before any API call. Invalid numbers
are collected in `result["invalid"]` and the valid ones are sent.

### Step 3: Handle the result

```python
if result["result"] == "OK":
    count = result.get("numbers", len(numbers))
    print(f"Sent to {count} numbers")

elif result["result"] == "PARTIAL":
    # Some batches succeeded, some failed
    for err in result["errors"]:
        print(f"Batch {err['batch']} failed: {err['description']}")

elif result["result"] == "ERROR":
    # All failed
    print(f"All batches failed: {result.get('errors', [])}")

# Always check for skipped numbers
if "invalid" in result:
    for entry in result["invalid"]:
        print(f"Skipped {entry['input']!r}: {entry['error']}")
```

---

## ERR013 (Queue Full) Retry

When `_send_bulk` encounters ERR013 (queue full, limit 1000 messages), it
retries automatically with exponential backoff:

| Attempt | Wait |
|---------|------|
| 1 | immediate |
| 2 | 30 seconds |
| 3 | 60 seconds |
| 4 | 120 seconds |

After 4 attempts the batch is recorded as an error in `result["errors"]`.

---

## Rate Limits

| Scenario | Behavior |
|----------|----------|
| ≤ 200 numbers | 1 API call, no delay |
| 201 to 400 numbers | 2 API calls, 0.5s between them |
| 401 to 600 numbers | 3 API calls, 0.5s between each |
| N numbers | ceil(N/200) calls, 0.5s between each |

The 0.5-second delay keeps the request rate at 2 per second, within the
kwtSMS safe limit.
