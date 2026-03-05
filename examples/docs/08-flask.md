# Example 08: Flask Integration

**File:** `examples/08-flask.py`
**Run:** `python examples/08-flask.py`

Flask blueprint with OTP send/verify endpoints and a health check route.
Uses the application factory pattern.

---

## Setup

### Install

```bash
pip install flask kwtsms
```

### Configure

```python
app.config.update({
    "KWTSMS_USERNAME":  "your_api_username",
    "KWTSMS_PASSWORD":  "your_api_password",
    "KWTSMS_SENDER_ID": "MY-BRAND",
    "KWTSMS_TEST_MODE": True,      # set to False in production
    "KWTSMS_LOG_FILE":  "kwtsms.log",
})
```

Or via environment variables (recommended for production):

```bash
export KWTSMS_USERNAME=your_api_username
export KWTSMS_PASSWORD=your_api_password
export KWTSMS_TEST_MODE=0
```

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Verify credentials and return balance |
| POST | `/otp/send` | Send OTP to a phone number |
| POST | `/otp/verify` | Verify submitted OTP |
| POST | `/sms/send` | Send arbitrary SMS (admin use only) |

---

## Step-by-Step

### Step 1: Create the application

```python
from flask import Flask
from kwtsms import KwtSMS


def create_app(config=None):
    app = Flask(__name__)
    app.config.update({
        "KWTSMS_USERNAME":  "your_api_username",
        "KWTSMS_PASSWORD":  "your_api_password",
        "KWTSMS_SENDER_ID": "KWT-SMS",
        "KWTSMS_TEST_MODE": True,
        "KWTSMS_LOG_FILE":  "kwtsms.log",
    })
    if config:
        app.config.update(config)

    def get_sms():
        if not hasattr(app, "_sms_client"):
            app._sms_client = KwtSMS(
                username=app.config["KWTSMS_USERNAME"],
                password=app.config["KWTSMS_PASSWORD"],
                sender_id=app.config["KWTSMS_SENDER_ID"],
                test_mode=app.config["KWTSMS_TEST_MODE"],
                log_file=app.config["KWTSMS_LOG_FILE"],
            )
        return app._sms_client

    return app
```

### Step 2: OTP send endpoint

```python
@app.post("/otp/send")
def otp_send():
    data  = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()

    if not phone:
        return jsonify({"error": "Phone number is required"}), 400

    code   = str(secrets.randbelow(1_000_000)).zfill(6)
    result = get_sms().send(phone, f"Your code is: {code}. Valid for 5 minutes.")

    if result["result"] != "OK":
        app.logger.error("kwtSMS send failed: %s", result)
        return jsonify({"error": "Could not send code. Try again."}), 500

    # Store with expiry (use Redis in production)
    _otp_store[phone] = {"code": code, "expires": time.time() + 300, "attempts": 0}
    return jsonify({"ok": True})
```

### Step 3: OTP verify endpoint

```python
@app.post("/otp/verify")
def otp_verify():
    data  = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    code  = str(data.get("code", "")).strip()

    entry = _otp_store.get(phone)
    if not entry:
        return jsonify({"ok": False, "error": "No code found. Request a new one."})
    if time.time() > entry["expires"]:
        del _otp_store[phone]
        return jsonify({"ok": False, "error": "Code expired. Request a new one."})
    if entry["attempts"] >= 5:
        del _otp_store[phone]
        return jsonify({"ok": False, "error": "Too many attempts. Request a new code."})
    if entry["code"] != code:
        _otp_store[phone]["attempts"] += 1
        return jsonify({"ok": False, "error": "Incorrect code."})

    del _otp_store[phone]
    return jsonify({"ok": True})
```

---

## Production Notes

| Topic | Recommendation |
|-------|----------------|
| OTP storage | Replace `_otp_store` dict with Redis (`flask-caching` or `redis-py`) |
| Rate limiting | Add `flask-limiter` before the OTP send endpoint |
| HTTPS | Always use TLS in production. Never send credentials or codes over HTTP |
| Error logging | Log `result` server-side, never expose `code` to the client |
| CAPTCHA | Add Cloudflare Turnstile or hCaptcha before OTP send |

---

## Running

```bash
# Development
flask --app examples/08-flask.py run

# Production (Gunicorn)
pip install gunicorn
gunicorn "examples.08_flask:create_app()" --bind 0.0.0.0:8000
```
