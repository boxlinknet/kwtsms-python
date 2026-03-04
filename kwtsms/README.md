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
result = sms.send("96598765432", "Your OTP is: 123456")  # send SMS
result = sms.send("96598765432", "Hello", sender="MY-APP")  # override sender
report = sms.validate(["96598765432", "+96512345678"])   # validate numbers
balance = sms.balance()
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
kwtsms setup                                  # first-time wizard
kwtsms verify
kwtsms balance
kwtsms send 96598765432 "Your OTP is: 123456"
kwtsms validate 96598765432 +96512345678
```

## Sender ID

`KWT-SMS` is a shared sender for **testing only**. Register a private sender ID on
[kwtsms.com](https://kwtsms.com) before going live — use a **Transactional** sender ID
for OTP messages to ensure delivery to DND numbers.

## License

MIT
