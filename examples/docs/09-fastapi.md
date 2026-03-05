# Example 09: FastAPI Integration

**File:** `examples/09-fastapi.py`
**Run:** `fastapi dev examples/09-fastapi.py`

FastAPI router with typed Pydantic request/response models, OTP send/verify
endpoints, and a health check. Automatically generates interactive API docs
at `/docs`.

---

## Setup

### Install

```bash
pip install "fastapi[standard]" kwtsms
```

### Configure

Set environment variables or create a `.env` file:

```ini
KWTSMS_USERNAME=your_api_username
KWTSMS_PASSWORD=your_api_password
KWTSMS_SENDER_ID=MY-BRAND
KWTSMS_TEST_MODE=1     # set to 0 in production
KWTSMS_LOG_FILE=kwtsms.log
```

### Run

```bash
fastapi dev examples/09-fastapi.py
# or
uvicorn examples.09_fastapi:app --reload
```

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Verify credentials and return balance |
| POST | `/otp/send` | Send OTP to a phone number |
| POST | `/otp/verify` | Verify submitted OTP |
| POST | `/sms/send` | Send arbitrary SMS (admin use only) |

---

## Request/Response Models

### POST /otp/send

Request:
```json
{"phone": "96598765432"}
```

Response (200 OK):
```json
{"ok": true}
```

Response (500 error):
```json
{"ok": false, "error": "Could not send verification code. Try again."}
```

### POST /otp/verify

Request:
```json
{"phone": "96598765432", "code": "123456"}
```

Response (success):
```json
{"ok": true}
```

Response (failure):
```json
{"ok": false, "error": "Incorrect code."}
```

### GET /health

Response:
```json
{"ok": true, "balance": 150.0, "error": null}
```

---

## Step-by-Step

### Step 1: Application factory

```python
from fastapi import FastAPI
from kwtsms import KwtSMS

def create_app() -> FastAPI:
    app = FastAPI()
    _sms = None

    def get_sms() -> KwtSMS:
        nonlocal _sms
        if _sms is None:
            _sms = KwtSMS.from_env()
        return _sms

    return app

app = create_app()
```

### Step 2: Pydantic models

```python
from pydantic import BaseModel, Field

class OTPSendRequest(BaseModel):
    phone: str = Field(..., example="96598765432")

class OTPVerifyRequest(BaseModel):
    phone: str
    code:  str = Field(..., min_length=4, max_length=8)
```

FastAPI validates request bodies against these models automatically. Invalid
requests return 422 Unprocessable Entity with structured error details.

### Step 3: OTP endpoint

```python
@app.post("/otp/send")
def otp_send(body: OTPSendRequest):
    code = str(secrets.randbelow(1_000_000)).zfill(6)
    result = get_sms().send(body.phone, f"Your code is: {code}. Valid for 5 minutes.")

    if result["result"] != "OK":
        raise HTTPException(status_code=500, detail="Could not send code.")

    _otp_store[body.phone] = {"code": code, "expires": time.time() + 300, "attempts": 0}
    return {"ok": True}
```

---

## Production Notes

| Topic | Recommendation |
|-------|----------------|
| OTP storage | Replace `_otp_store` dict with Redis (`aioredis` or `redis-py`) |
| Rate limiting | Add `slowapi` middleware |
| Authentication | Protect `/sms/send` with OAuth2 or API key via `fastapi.security` |
| Background tasks | Use `BackgroundTasks` or `Celery` to send SMS asynchronously |
| HTTPS | Use HTTPS in production with a reverse proxy (Nginx, Caddy) |
| Dependency injection | Inject `KwtSMS` via `Depends()` for testability |

### Dependency injection pattern

```python
from fastapi import Depends

def get_sms_client() -> KwtSMS:
    return KwtSMS.from_env()

@app.post("/otp/send")
def otp_send(body: OTPSendRequest, sms: KwtSMS = Depends(get_sms_client)):
    result = sms.send(body.phone, "Your code is: 123456")
    ...
```

This makes the client easy to mock in tests:

```python
from fastapi.testclient import TestClient

def mock_sms():
    from unittest.mock import MagicMock
    m = MagicMock()
    m.send.return_value = {"result": "OK", "msg-id": "test123", ...}
    return m

app.dependency_overrides[get_sms_client] = mock_sms
client = TestClient(app)
```
