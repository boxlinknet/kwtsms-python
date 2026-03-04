# kwtsms

Python client for the [kwtSMS API](https://kwtsms.com) — Kuwait SMS gateway.

Zero external dependencies. Python 3.8+.

## Install

```bash
pip install kwtsms
```

## Quick start

```python
from kwtsms import KwtSMS

sms = KwtSMS.from_env()                              # reads .env or env vars
ok, balance, err = sms.verify()                      # test credentials
result = sms.send("96598765432", "Your OTP is: 123456")
result = sms.send("96598765432", "Hello", sender="MY-APP")  # override sender
result = sms.send(["96598765432", "+96512345678"], "Hello!")  # multiple numbers

# Every error response includes an 'action' field with developer guidance
if result["result"] == "ERROR":
    print(result["code"])        # e.g. "ERR003"
    print(result["description"]) # human-readable error
    print(result["action"])      # what to do next

# Invalid numbers are reported per-number, not raised
result = sms.send(["96598765432", "abc", "user@gmail.com"], "Hi")
# result["invalid"] → [{"input": "abc", "error": "..."}, ...]

report = sms.validate(["96598765432", "+96512345678", "123"])
# report["ok"] → valid, report["er"] → format error, report["nr"] → no route
# report["rejected"] → pre-rejected with per-number error messages
balance = sms.balance()
```

## Utility functions

```python
from kwtsms import normalize_phone, validate_phone_input, clean_message

normalize_phone("+965 9876-5432")       # → "96598765432"
validate_phone_input("user@gmail.com")  # → (False, "is an email address...", "")
validate_phone_input("+96598765432")    # → (True, None, "96598765432")
clean_message("OTP: ١٢٣٤٥٦ 🎉")       # → "OTP: 123456 "
```

## Configuration

Create a `.env` file (or set environment variables):

```ini
KWTSMS_USERNAME=your_api_user
KWTSMS_PASSWORD=your_api_pass
KWTSMS_SENDER_ID=YOUR-SENDERID   # use KWT-SMS for testing only
KWTSMS_TEST_MODE=1                # 1 = test (safe default), 0 = live
KWTSMS_LOG_FILE=kwtsms.log
```

Or run the setup wizard:

```bash
kwtsms setup
```

## CLI

```bash
kwtsms setup                                          # first-time wizard
kwtsms verify                                         # test credentials
kwtsms balance                                        # check balance
kwtsms send 96598765432 "Your OTP is: 123456"        # send SMS
kwtsms send 96598765432,96512345678 "Hello!"          # multiple numbers (no spaces around commas)
kwtsms send "96598765432, 96512345678" "Hello!"       # or quote the whole list (spaces OK inside quotes)
kwtsms send 96598765432 "Hello" --sender MY-APP       # override sender ID
kwtsms send 96598765432 "Hello" --sender "kwt sms"   # sender ID with spaces — quote it
kwtsms validate 96598765432 +96512345678              # validate numbers
```

## Sender ID

`KWT-SMS` is a shared sender for **testing only**. Register a private sender ID on
[kwtsms.com](https://kwtsms.com) before going live — use a **Transactional** sender ID
for OTP messages to ensure delivery to DND numbers.

## License

MIT
