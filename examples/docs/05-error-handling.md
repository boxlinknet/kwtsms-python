# Example 05: Error Handling

**File:** `examples/05-error-handling.py`
**Run:** `python examples/05-error-handling.py`

Every error from `send()`, `verify()`, `validate()`, and `balance()` is
returned as a dict. This client never raises on API errors or network
failures. This example shows every error category and the correct response.

---

## Error Response Structure

```python
{
    "result":      "ERROR",
    "code":        "ERR003",
    "description": "Authentication error...",
    "action":      "Wrong API username or password. Check KWTSMS_USERNAME...",
}
```

The `action` field is added by this client (not by the API). It gives
developer-friendly guidance for every known error code.

OK responses never contain `code` or `action`.

---

## Error Categories

### Category 1: Invalid input (local, no API call)

These are caught before any API call. No credits are consumed.

| Code | When | Fix |
|------|------|-----|
| `ERR_INVALID_INPUT` | Empty phone, email, too short, no digits | Fix the phone number |
| `ERR009` | Message empty after cleaning (emoji-only) | Use plain text |

```python
result = sms.send("", "Test")
# {"result": "ERROR", "code": "ERR_INVALID_INPUT", "description": "Phone number is required", ...}

result = sms.send("96598765432", "👋🔥")
# {"result": "ERROR", "code": "ERR009", "description": "Message is empty after cleaning...", ...}
```

### Category 2: Authentication errors

| Code | Meaning | Fix |
|------|---------|-----|
| `ERR003` | Wrong API username or password | Fix `KWTSMS_USERNAME` / `KWTSMS_PASSWORD` in `.env` |
| `ERR004` | API access not enabled | Contact kwtSMS support |
| `ERR005` | Account blocked | Contact kwtSMS support |
| `ERR024` | IP not in whitelist | Add server IP at kwtsms.com: Account: API: IP Lockdown |

### Category 3: Sender ID errors

| Code | Meaning | Fix |
|------|---------|-----|
| `ERR008` | Sender ID not registered or banned | Register at kwtsms.com: Sender IDs. Note: case-sensitive |
| `ERR002` | Required parameter missing | Check that sender, mobile, and message are all provided |

### Category 4: Balance errors

| Code | Meaning | Fix |
|------|---------|-----|
| `ERR010` | Zero balance | Recharge credits at kwtsms.com |
| `ERR011` | Insufficient balance for this batch | Buy more credits |

### Category 5: Phone number errors

| Code | Meaning | Fix |
|------|---------|-----|
| `ERR006` | No valid phone numbers | Include country code (96598765432, not 98765432) |
| `ERR025` | Invalid phone number format | Check number format |
| `ERR026` | Country not activated | Contact kwtSMS support to enable the country |
| `ERR028` | Too fast (< 15s since last send to this number) | Wait 15 seconds |

### Category 6: Message errors

| Code | Meaning | Fix |
|------|---------|-----|
| `ERR009` | Empty message | Provide non-empty text |
| `ERR012` | Message too long (> 6 SMS pages) | Shorten the message |
| `ERR027` | HTML tags in message | Remove HTML, use plain text |
| `ERR031` | Bad language detected | Remove prohibited content |
| `ERR032` | Spam detected | Check message content and send frequency |

### Category 7: Network errors

| Code | Meaning | Fix |
|------|---------|-----|
| `NETWORK` | No internet, timeout, DNS failure, firewall | Check connectivity; retry |

`send()` never raises on network failures. All errors are returned as dicts.

---

## Recommended Production Pattern

```python
result = sms.send(phone, message)

if result["result"] == "OK":
    save_msg_id(result["msg-id"])
    update_balance_cache(result["balance-after"])

elif result["result"] == "ERROR":
    code = result.get("code", "UNKNOWN")

    # Map codes to your application actions
    if code in ("ERR003", "ERR004", "ERR005"):
        alert_ops("kwtSMS auth error")
    elif code in ("ERR010", "ERR011"):
        alert_ops("kwtSMS low balance")
    elif code == "NETWORK":
        schedule_retry(phone, message, delay_seconds=30)

    # Never expose raw error codes to end users
    show_user("We couldn't send your message. Please try again.")
```

---

## verify() Error Handling

```python
ok, balance, error = sms.verify()
if not ok:
    # error includes both description and action:
    # "Authentication error... -> Wrong API username or password..."
    print(error)
```

`verify()` is the right place to catch configuration errors at startup. Run
it once when your application starts.
