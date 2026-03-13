"""
kwtsms: Python client for the kwtSMS API (kwtsms.com)

Quick start:
    from kwtsms import KwtSMS

    sms = KwtSMS.from_env()                          # reads .env / env vars
    ok, balance, err = sms.verify()
    result = sms.send("96598765432", "Your OTP is: 123456")
    result = sms.send("96598765432", "Hello", sender="MY-APP")  # override sender
    report = sms.validate(["96598765432", "+96512345678"])
    balance = sms.balance()
    delivery = sms.status(result["msg-id"])                  # delivery report
    result = sms.send_with_retry("96598765432", "Hello")     # auto-retry on ERR028
    sms = AsyncKwtSMS.from_env()                     # async client (pip install kwtsms[async])

Utility functions:
    from kwtsms import normalize_phone, clean_message, validate_phone_input, parse_webhook
"""

from kwtsms._core import (KwtSMS, clean_message, normalize_phone,
                          validate_phone_input, parse_webhook,
                          find_country_code, validate_phone_format)
from kwtsms._async import AsyncKwtSMS

__all__ = ["KwtSMS", "AsyncKwtSMS", "normalize_phone", "clean_message",
           "validate_phone_input", "parse_webhook",
           "find_country_code", "validate_phone_format"]
__version__ = "0.7.36"
