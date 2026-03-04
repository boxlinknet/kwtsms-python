"""
kwtsms — Python client for the kwtSMS API (kwtsms.com)

Quick start:
    from kwtsms import KwtSMS

    sms = KwtSMS.from_env()                          # reads .env / env vars
    ok, balance, err = sms.verify()
    result = sms.send("96598765432", "Your OTP is: 123456")
    result = sms.send("96598765432", "Hello", sender="MY-APP")  # override sender
    report = sms.validate(["96598765432", "+96512345678"])
    balance = sms.balance()

Utility functions:
    from kwtsms import normalize_phone, clean_message
"""

from kwtsms._core import KwtSMS, clean_message, normalize_phone

__all__ = ["KwtSMS", "normalize_phone", "clean_message"]
__version__ = "0.1.0"
