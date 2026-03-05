# Example 07: Django Integration

**File:** `examples/07-django.py`

Integrate kwtSMS into a Django project. Covers three patterns: a reusable
service class, a class-based OTP view, and a management command.

---

## Setup

### Install

```bash
pip install kwtsms
```

### Configure settings.py

```python
KWTSMS_USERNAME  = "your_api_username"
KWTSMS_PASSWORD  = "your_api_password"
KWTSMS_SENDER_ID = "MY-BRAND"
KWTSMS_TEST_MODE = True       # set to False in production
KWTSMS_LOG_FILE  = "kwtsms.log"
```

---

## Pattern 1: SMSService

Place this in `your_app/services/sms.py`.

```python
from django.conf import settings
from kwtsms import KwtSMS


class SMSService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = KwtSMS(
                username=settings.KWTSMS_USERNAME,
                password=settings.KWTSMS_PASSWORD,
                sender_id=settings.KWTSMS_SENDER_ID,
                test_mode=settings.KWTSMS_TEST_MODE,
                log_file=settings.KWTSMS_LOG_FILE,
            )
        return self._client

    def send(self, phone: str, message: str, sender: str = None) -> dict:
        return self._get_client().send(phone, message, sender=sender)

    def verify(self) -> tuple:
        return self._get_client().verify()

    def balance(self) -> float | None:
        return self._get_client().balance()


sms = SMSService()  # singleton
```

Usage in any view or task:

```python
from your_app.services.sms import sms

result = sms.send("96598765432", "Your order is ready.")
```

---

## Pattern 2: OTP View

Place this in `your_app/views/otp.py`.

```python
import json
import secrets
import time

from django.core.cache import cache
from django.http import JsonResponse
from django.views import View

from your_app.services.sms import sms


class OTPView(View):
    OTP_TTL      = 300   # 5 minutes
    MAX_ATTEMPTS = 5
    APP_NAME     = "MyApp"

    def post(self, request, action):
        if action == "send":
            return self._send(request)
        if action == "verify":
            return self._verify(request)
        return JsonResponse({"error": "Not found"}, status=404)

    def _send(self, request):
        body  = json.loads(request.body)
        phone = body.get("phone", "").strip()

        if not phone:
            return JsonResponse({"error": "Phone number is required"}, status=400)

        code = str(secrets.randbelow(1_000_000)).zfill(6)
        result = sms.send(phone, f"Your {self.APP_NAME} code is: {code}. Valid for 5 minutes.")

        if result["result"] != "OK":
            return JsonResponse({"error": "Could not send code. Try again."}, status=500)

        cache.set(f"otp:{phone}", {"code": code, "attempts": 0}, timeout=self.OTP_TTL)
        return JsonResponse({"ok": True})

    def _verify(self, request):
        body  = json.loads(request.body)
        phone = body.get("phone", "").strip()
        code  = body.get("code", "").strip()
        entry = cache.get(f"otp:{phone}")

        if not entry:
            return JsonResponse({"ok": False, "error": "Code expired. Request a new one."})

        if entry["attempts"] >= self.MAX_ATTEMPTS:
            cache.delete(f"otp:{phone}")
            return JsonResponse({"ok": False, "error": "Too many attempts. Request a new code."})

        if entry["code"] != code:
            entry["attempts"] += 1
            cache.set(f"otp:{phone}", entry, timeout=self.OTP_TTL)
            return JsonResponse({"ok": False, "error": "Incorrect code."})

        cache.delete(f"otp:{phone}")
        return JsonResponse({"ok": True})
```

Register the URL in `urls.py`:

```python
from django.urls import path
from your_app.views.otp import OTPView

urlpatterns = [
    path("otp/<str:action>/", OTPView.as_view()),
]
```

---

## Pattern 3: Management Command

Place in `your_app/management/commands/send_sms.py`:

```python
from django.core.management.base import BaseCommand
from your_app.services.sms import sms


class Command(BaseCommand):
    help = "Send SMS or verify credentials via kwtSMS"

    def add_arguments(self, parser):
        parser.add_argument("--phone",   type=str)
        parser.add_argument("--message", type=str)
        parser.add_argument("--verify",  action="store_true")

    def handle(self, *args, **options):
        if options["verify"]:
            ok, balance, error = sms.verify()
            if ok:
                self.stdout.write(self.style.SUCCESS(f"OK. Balance: {balance} credits"))
            else:
                self.stderr.write(f"Error: {error}")
            return

        result = sms.send(options["phone"], options["message"])
        if result["result"] == "OK":
            self.stdout.write(self.style.SUCCESS(f"Sent. msg-id={result['msg-id']}"))
        else:
            self.stderr.write(f"Failed [{result['code']}]: {result['description']}")
```

Usage:

```bash
python manage.py send_sms --verify
python manage.py send_sms --phone 96598765432 --message "Hello"
```

---

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImproperlyConfigured` | Settings not loaded | Make sure `django.setup()` is called or run inside a request context |
| `AttributeError: 'Settings' has no attribute 'KWTSMS_USERNAME'` | Setting missing | Add to `settings.py` |
| Cache backend not configured | `cache.set()` silently fails | Add a cache backend in `settings.py` (e.g., Redis or LocMem) |
