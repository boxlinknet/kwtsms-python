# Reference

Quick lookup for phone number formats, Sender ID rules, error codes, and
the pre-launch checklist.

---

## Phone Number Format Reference

### Accepted inputs (all normalized to the same output)

| Input | Normalized | Notes |
|-------|-----------|-------|
| `96598765432` | `96598765432` | Already normalized |
| `+96598765432` | `96598765432` | Leading `+` stripped |
| `0096598765432` | `96598765432` | Leading `00` stripped |
| `+965 9876 5432` | `96598765432` | Spaces stripped |
| `+965-9876-5432` | `96598765432` | Dashes stripped |
| `(965) 9876 5432` | `96598765432` | Brackets stripped |
| `٩٦٥٩٨٧٦٥٤٣٢` | `96598765432` | Arabic-Indic digits |
| `۹۶۵۹۸۷۶۵۴۳۲` | `96598765432` | Extended Arabic-Indic (Persian) |
| `  96598765432  ` | `96598765432` | Leading/trailing whitespace |

### Rejected inputs

| Input | Error | Code |
|-------|-------|------|
| `""` | Phone number is required | `ERR_INVALID_INPUT` |
| `"user@example.com"` | Email address, not a phone number | `ERR_INVALID_INPUT` |
| `"123"` | Too short (3 digits, minimum is 7) | `ERR_INVALID_INPUT` |
| `"abcdef"` | No digits found | `ERR_INVALID_INPUT` |
| `"1234567890123456"` | Too long (16 digits, maximum is 15) | `ERR_INVALID_INPUT` |

---

## Sender ID

### Types

| Type | Cost | Delivery | Use for |
|------|------|----------|---------|
| Promotional | Free | Blocked for DND numbers | Marketing, newsletters |
| Transactional | ~15 KD | Delivered to all including DND | OTP, alerts, account notifications |

### Rules

- Maximum 11 alphanumeric characters (A-Z, 0-9)
- No spaces, hyphens, or special characters in the Sender ID itself
- Case-sensitive: `KWT-SMS` is not the same as `kwt-sms`
- Must be registered on your account before use
- Register at kwtsms.com: Account: Sender IDs

### Default Sender ID

The default `KWT-SMS` is a shared Promotional Sender ID. It is fine for
testing but must be replaced with a private registered Sender ID before going
to production. Using a shared Sender ID means other accounts can send with
the same name, which harms deliverability and brand recognition.

---

## Error Code Reference

### Authentication and account

| Code | Description | Action |
|------|-------------|--------|
| `ERR001` | API disabled on account | Enable at kwtsms.com: Account: API |
| `ERR003` | Wrong username or password | Fix `KWTSMS_USERNAME` / `KWTSMS_PASSWORD` in `.env` |
| `ERR004` | No API access | Contact kwtSMS support |
| `ERR005` | Account blocked | Contact kwtSMS support |
| `ERR024` | IP not in whitelist | Add server IP at kwtsms.com: Account: API: IP Lockdown |

### Sender ID

| Code | Description | Action |
|------|-------------|--------|
| `ERR002` | Required parameter missing | Check sender, mobile, and message are all provided |
| `ERR008` | Sender ID banned or not found | Register the Sender ID at kwtsms.com. Check case |

### Phone numbers

| Code | Description | Action |
|------|-------------|--------|
| `ERR006` | No valid phone numbers | Include country code (96598765432, not 98765432) |
| `ERR007` | Too many numbers (> 200) | Use `send()` with a list: it batches automatically |
| `ERR025` | Invalid phone number | Check number format includes country code |
| `ERR026` | Country not activated | Contact kwtSMS support to enable the destination country |
| `ERR028` | Too fast (< 15s since last send to this number) | Wait 15 seconds |

### Message

| Code | Description | Action |
|------|-------------|--------|
| `ERR009` | Empty message | Provide non-empty text. Emoji-only messages are caught locally |
| `ERR012` | Message too long (> 6 SMS pages) | Shorten the message |
| `ERR027` | HTML tags in message | Remove HTML. `send()` strips HTML automatically via `clean_message()` |
| `ERR031` | Bad language detected | Review message content |
| `ERR032` | Spam detected | Review message content and send frequency |

### Balance

| Code | Description | Action |
|------|-------------|--------|
| `ERR010` | Zero balance | Recharge credits at kwtsms.com |
| `ERR011` | Insufficient balance | Buy more credits at kwtsms.com |

### Queue and delivery

| Code | Description | Action |
|------|-------------|--------|
| `ERR013` | Queue full (1000 messages) | Wait and retry. `_send_bulk()` retries automatically with backoff |
| `ERR030` | Message stuck in queue with error | Delete at kwtsms.com: Queue to recover credits |
| `ERR033` | No active coverage | Contact kwtSMS support |

### Delivery reports

| Code | Description | Action |
|------|-------------|--------|
| `ERR019` | No delivery reports found | Check the `msg-id` is correct |
| `ERR020` | Message ID does not exist | Save `msg-id` from the send response |
| `ERR021` | Report not ready yet | Try again after delivery time |
| `ERR022` | Reports not ready (try after 24h) | Wait 24 hours |
| `ERR023` | Unknown report error | Contact kwtSMS support |
| `ERR029` | Message ID incorrect | Check the `msg-id` value |

### Client-side codes (not from API)

| Code | Description | Action |
|------|-------------|--------|
| `ERR_INVALID_INPUT` | Phone number failed local validation | Fix the phone number |
| `NETWORK` | Network error, timeout, DNS failure | Check connectivity; retry |

---

## Pre-Launch Checklist

### Credentials

- [ ] `KWTSMS_USERNAME` and `KWTSMS_PASSWORD` are API credentials, not account phone or website login
- [ ] `verify()` returns `ok=True` and a non-zero balance
- [ ] `KWTSMS_TEST_MODE` is set to `0` (or `False`) in production

### Sender ID

- [ ] A private Sender ID is registered on the account
- [ ] `KWTSMS_SENDER_ID` is set to the private ID (not `KWT-SMS`)
- [ ] OTP / transactional flows use a Transactional Sender ID

### Security

- [ ] `.env` file has `600` permissions: `chmod 600 .env`
- [ ] `.env` is in `.gitignore` (never committed to version control)
- [ ] Raw error codes (`ERR003`, etc.) are never shown to end users
- [ ] OTP codes are stored hashed, not in plaintext
- [ ] Rate limiting is enabled for OTP send endpoints
- [ ] CAPTCHA is enabled for OTP send endpoints
- [ ] Credentials are stored as environment variables, not hardcoded

### Content

- [ ] All messages pass `clean_message()` (no emojis, no HTML)
- [ ] Message includes the app name so users recognize it
- [ ] OTP messages include expiry time
- [ ] Messages are under 160 characters (1 credit per SMS)

### Anti-abuse

- [ ] Brute-force protection is enabled (max 5 attempts per OTP)
- [ ] OTPs expire after 5 minutes
- [ ] Used OTPs are deleted immediately after verification
