"""
Example 09: FastAPI Integration
---------------------------------
FastAPI router with OTP send/verify endpoints, a health check, and Pydantic
request/response models.

Install:
    pip install "fastapi[standard]" kwtsms

Configure via environment variables or a .env file:
    KWTSMS_USERNAME=your_api_username
    KWTSMS_PASSWORD=your_api_password
    KWTSMS_SENDER_ID=MY-BRAND
    KWTSMS_TEST_MODE=1     # set to 0 in production
    KWTSMS_LOG_FILE=kwtsms.log

Run:
    fastapi dev examples/09-fastapi.py
    # or
    uvicorn examples.09_fastapi:app --reload

Endpoints:
    GET  /health        (verify credentials)
    POST /otp/send      (send OTP)
    POST /otp/verify    (verify OTP)
    POST /sms/send      (send arbitrary SMS, admin use only)

Interactive docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import secrets
import time
from typing import Dict, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    _fastapi_available = True
except ImportError:
    _fastapi_available = False
    print("FastAPI not installed. Install with: pip install 'fastapi[standard]'")

from kwtsms import KwtSMS


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> "FastAPI":
    if not _fastapi_available:
        raise RuntimeError("Install FastAPI: pip install 'fastapi[standard]'")

    app = FastAPI(
        title="kwtSMS FastAPI Example",
        description="OTP send/verify and direct SMS via kwtSMS.",
        version="1.0.0",
    )

    # ── kwtSMS client (initialized from .env on first use) ────────────────────

    _sms: Optional[KwtSMS] = None

    def get_sms() -> KwtSMS:
        nonlocal _sms
        if _sms is None:
            _sms = KwtSMS.from_env()
        return _sms

    # ── In-memory OTP store (replace with Redis in production) ───────────────

    _otp_store: Dict[str, dict] = {}
    OTP_TTL      = 300   # seconds (5 minutes)
    MAX_ATTEMPTS = 5

    # ── Pydantic models ───────────────────────────────────────────────────────

    class OTPSendRequest(BaseModel):
        phone: str = Field(..., example="96598765432", description="Phone number with country code")

    class OTPVerifyRequest(BaseModel):
        phone: str  = Field(..., example="96598765432")
        code:  str  = Field(..., example="123456", min_length=4, max_length=8)

    class SMSSendRequest(BaseModel):
        phone:   str            = Field(..., example="96598765432")
        message: str            = Field(..., min_length=1)
        sender:  Optional[str]  = Field(None, example="MY-BRAND")

    class SuccessResponse(BaseModel):
        ok: bool = True

    class ErrorResponse(BaseModel):
        ok:    bool = False
        error: str

    class HealthResponse(BaseModel):
        ok:      bool
        balance: Optional[float] = None
        error:   Optional[str]   = None

    class SMSSendResponse(BaseModel):
        ok:             bool
        msg_id:         Optional[str]   = None
        points_charged: Optional[int]   = None
        balance_after:  Optional[float] = None

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse)
    def health():
        """Verify kwtSMS credentials and return current balance."""
        ok, balance, error = get_sms().verify()
        return HealthResponse(ok=ok, balance=balance, error=error)

    @app.post("/otp/send", response_model=SuccessResponse, responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    })
    def otp_send(body: OTPSendRequest):
        """
        Send a 6-digit OTP to the given phone number.

        The OTP is valid for 5 minutes. Store the returned success status;
        the actual code is never returned in the response.
        """
        phone = body.phone.strip()
        if not phone:
            raise HTTPException(status_code=400, detail="Phone number is required")

        code = str(secrets.randbelow(1_000_000)).zfill(6)
        result = get_sms().send(phone, f"Your verification code is: {code}. Valid for 5 minutes.")

        if result["result"] != "OK":
            # Log full error server-side; never expose raw API codes to clients
            import logging
            logging.error("kwtSMS send failed: %s", result)
            raise HTTPException(status_code=500, detail="Could not send verification code. Try again.")

        _otp_store[phone] = {
            "code":     code,
            "expires":  time.time() + OTP_TTL,
            "attempts": 0,
        }

        return SuccessResponse()

    @app.post("/otp/verify", response_model=SuccessResponse, responses={
        422: {"model": ErrorResponse},
    })
    def otp_verify(body: OTPVerifyRequest):
        """
        Verify the OTP submitted by the user.

        Returns 200 with ok=True on success.
        Returns 200 with ok=False and an error message on failure (wrong code, expired, too many attempts).
        """
        phone = body.phone.strip()
        code  = body.code.strip()

        entry = _otp_store.get(phone)

        if not entry:
            return ErrorResponse(error="No code found. Request a new one.")

        if time.time() > entry["expires"]:
            del _otp_store[phone]
            return ErrorResponse(error="Code expired. Request a new one.")

        if entry["attempts"] >= MAX_ATTEMPTS:
            del _otp_store[phone]
            return ErrorResponse(error="Too many attempts. Request a new code.")

        if entry["code"] != code:
            _otp_store[phone]["attempts"] += 1
            return ErrorResponse(error="Incorrect code.")

        del _otp_store[phone]
        return SuccessResponse()

    @app.post("/sms/send", response_model=SMSSendResponse, responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    })
    def sms_send(body: SMSSendRequest):
        """
        Send an SMS directly. Protect this endpoint with authentication in production.
        """
        if not body.phone or not body.message:
            raise HTTPException(status_code=400, detail="phone and message are required")

        result = get_sms().send(body.phone, body.message, sender=body.sender)

        if result["result"] == "OK":
            return SMSSendResponse(
                ok=True,
                msg_id=result.get("msg-id"),
                points_charged=result.get("points-charged"),
                balance_after=result.get("balance-after"),
            )

        raise HTTPException(
            status_code=500,
            detail=f"[{result.get('code')}] {result.get('description')}",
        )

    return app


# ── Create the app instance (used by uvicorn/fastapi dev) ────────────────────

if _fastapi_available:
    app = create_app()

if __name__ == "__main__":
    if not _fastapi_available:
        raise SystemExit("Install FastAPI first: pip install 'fastapi[standard]'")

    import uvicorn
    print("Starting FastAPI dev server at http://127.0.0.1:8000")
    print("Interactive docs: http://127.0.0.1:8000/docs")
    uvicorn.run("examples.09_fastapi:app", host="127.0.0.1", port=8000, reload=True)
