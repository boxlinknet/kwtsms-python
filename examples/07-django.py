"""
Example 07: Django Integration
--------------------------------
SMS service class, Django view, and management command.

This file shows three integration patterns:
    1. SMSService: a reusable service class configured via Django settings
    2. OTPView: a class-based view for OTP send/verify endpoints
    3. send_sms management command: run from the terminal

Install:
    pip install django kwtsms

Configure settings.py:
    KWTSMS_USERNAME = "your_api_username"
    KWTSMS_PASSWORD = "your_api_password"
    KWTSMS_SENDER_ID = "MY-BRAND"
    KWTSMS_TEST_MODE = True       # set to False in production
    KWTSMS_LOG_FILE = "kwtsms.log"

This file is a reference, not a runnable script.
To run the management command, place it in your_app/management/commands/send_sms.py.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. SMS Service (your_app/services/sms.py)
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import secrets

# Lazy import so this module can be imported without Django installed
try:
    from django.conf import settings
    _django_available = True
except ImportError:
    _django_available = False


class SMSService:
    """
    Thin wrapper around KwtSMS, configured via Django settings.

    Usage:
        from your_app.services.sms import sms
        result = sms.send("96598765432", "Hello!")

    Singleton pattern: import `sms` directly, not the class.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from kwtsms import KwtSMS
            self._client = KwtSMS(
                username=getattr(settings, "KWTSMS_USERNAME", ""),
                password=getattr(settings, "KWTSMS_PASSWORD", ""),
                sender_id=getattr(settings, "KWTSMS_SENDER_ID", "KWT-SMS"),
                test_mode=getattr(settings, "KWTSMS_TEST_MODE", True),
                log_file=getattr(settings, "KWTSMS_LOG_FILE", "kwtsms.log"),
            )
        return self._client

    def send(self, phone: str, message: str, sender: str = None) -> dict:
        return self._get_client().send(phone, message, sender=sender)

    def verify(self) -> tuple:
        return self._get_client().verify()

    def balance(self) -> float | None:
        return self._get_client().balance()


# Singleton: import `sms` in your views, not the class
sms = SMSService()


# ─────────────────────────────────────────────────────────────────────────────
# 2. OTP View (your_app/views/otp.py)
# ─────────────────────────────────────────────────────────────────────────────

# In a real Django project you would import these properly:
#   from django.http import JsonResponse
#   from django.views import View
#   from django.core.cache import cache

# This example uses stubs so the file parses without Django installed.

def JsonResponse(data, status=200):  # noqa: N802 (stub)
    return {"body": data, "status": status}


class OTPView:
    """
    Handles OTP send and verify over HTTP.

    URLs (urls.py):
        from your_app.views.otp import OTPView
        path("otp/send/",   OTPView.as_view(), name="otp-send"),
        path("otp/verify/", OTPView.as_view(), name="otp-verify"),

    POST /otp/send/
        Body: {"phone": "96598765432"}
        Response: {"ok": true} or {"error": "..."}

    POST /otp/verify/
        Body: {"phone": "96598765432", "code": "123456"}
        Response: {"ok": true} or {"ok": false, "error": "..."}
    """

    OTP_TTL = 300        # seconds (5 minutes)
    MAX_ATTEMPTS = 5
    APP_NAME = "MyApp"

    def post_send(self, request):
        import json
        body  = json.loads(request.body)
        phone = body.get("phone", "").strip()

        if not phone:
            return JsonResponse({"error": "Phone number is required"}, status=400)

        code = str(secrets.randbelow(1_000_000)).zfill(6)

        result = sms.send(phone, f"Your {self.APP_NAME} code is: {code}. Expires in 5 minutes.")

        if result["result"] != "OK":
            # Never expose raw API error codes to users
            return JsonResponse({"error": "Could not send verification code. Try again."}, status=500)

        # Store in Django cache (requires CACHES in settings.py)
        # cache.set(f"otp:{phone}", {"code": code, "attempts": 0}, timeout=self.OTP_TTL)

        return JsonResponse({"ok": True})

    def post_verify(self, request):
        import json
        body  = json.loads(request.body)
        phone = body.get("phone", "").strip()
        code  = body.get("code", "").strip()

        # entry = cache.get(f"otp:{phone}")
        entry = None  # stub: replace with cache.get in real code

        if not entry:
            return JsonResponse({"ok": False, "error": "Code expired. Request a new one."})

        if entry["attempts"] >= self.MAX_ATTEMPTS:
            # cache.delete(f"otp:{phone}")
            return JsonResponse({"ok": False, "error": "Too many attempts. Request a new code."})

        if entry["code"] != code:
            entry["attempts"] += 1
            # cache.set(f"otp:{phone}", entry, timeout=self.OTP_TTL)
            return JsonResponse({"ok": False, "error": "Incorrect code."})

        # cache.delete(f"otp:{phone}")
        return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────────
# 3. Management Command (your_app/management/commands/send_sms.py)
# ─────────────────────────────────────────────────────────────────────────────

# Place this class in: your_app/management/commands/send_sms.py
#
# Usage:
#   python manage.py send_sms --phone 96598765432 --message "Hello"
#   python manage.py send_sms --verify

MANAGEMENT_COMMAND_TEMPLATE = '''
from django.core.management.base import BaseCommand

# Import SMSService from your app
# from your_app.services.sms import sms

class Command(BaseCommand):
    help = "Send SMS via kwtSMS or verify credentials"

    def add_arguments(self, parser):
        parser.add_argument("--phone",   type=str, help="Recipient phone number")
        parser.add_argument("--message", type=str, help="SMS message text")
        parser.add_argument("--verify",  action="store_true", help="Verify credentials and print balance")

    def handle(self, *args, **options):
        if options["verify"]:
            ok, balance, error = sms.verify()
            if ok:
                self.stdout.write(self.style.SUCCESS(f"Connected. Balance: {balance} credits"))
            else:
                self.stderr.write(f"Error: {error}")
            return

        phone   = options["phone"]
        message = options["message"]

        if not phone or not message:
            self.stderr.write("Both --phone and --message are required.")
            return

        result = sms.send(phone, message)

        if result["result"] == "OK":
            self.stdout.write(self.style.SUCCESS(
                f"Sent. msg-id={result[\'msg-id\']} credits={result[\'points-charged\']}"
            ))
        else:
            self.stderr.write(f"Failed [{result[\'code\']}]: {result[\'description\']}")
'''

print("Django integration patterns loaded.")
print("See the source of this file for:")
print("  1. SMSService class (wraps KwtSMS for Django settings)")
print("  2. OTPView (send + verify over HTTP)")
print("  3. Management command template (send_sms)")
