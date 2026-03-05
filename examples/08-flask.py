"""
Example 08: Flask Integration
--------------------------------
Flask blueprint with OTP send/verify endpoints.

Install:
    pip install flask kwtsms

Configure your app:
    app.config["KWTSMS_USERNAME"] = "your_api_username"
    app.config["KWTSMS_PASSWORD"] = "your_api_password"
    app.config["KWTSMS_SENDER_ID"] = "MY-BRAND"
    app.config["KWTSMS_TEST_MODE"] = True    # set to False in production
    app.config["KWTSMS_LOG_FILE"]  = "kwtsms.log"

Run (development):
    flask --app examples/08-flask.py run

This file is a self-contained runnable example.
For production, split into a blueprint module and use a proper app factory.
"""

from __future__ import annotations

import secrets
import time
from typing import Dict

# ── Flask application factory ────────────────────────────────────────────────

try:
    from flask import Flask, jsonify, request
    _flask_available = True
except ImportError:
    _flask_available = False
    print("Flask not installed. Install with: pip install flask")
    print("This file demonstrates the integration pattern.")


def create_app(config: dict = None) -> "Flask":
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Default config. Override with environment variables in production.
    app.config.update({
        "KWTSMS_USERNAME": "your_api_username",
        "KWTSMS_PASSWORD": "your_api_password",
        "KWTSMS_SENDER_ID": "KWT-SMS",
        "KWTSMS_TEST_MODE": True,
        "KWTSMS_LOG_FILE":  "kwtsms.log",
        "SECRET_KEY":       "change-this-in-production",
    })

    if config:
        app.config.update(config)

    # Initialize kwtSMS client (lazy, initialized on first request)
    from kwtsms import KwtSMS

    def get_sms() -> KwtSMS:
        """Get or create the kwtSMS client from Flask config."""
        if not hasattr(app, "_sms_client"):
            app._sms_client = KwtSMS(
                username=app.config["KWTSMS_USERNAME"],
                password=app.config["KWTSMS_PASSWORD"],
                sender_id=app.config["KWTSMS_SENDER_ID"],
                test_mode=app.config["KWTSMS_TEST_MODE"],
                log_file=app.config["KWTSMS_LOG_FILE"],
            )
        return app._sms_client

    # ── In-memory OTP store (replace with Redis or DB in production) ──────────

    _otp_store: Dict[str, dict] = {}
    OTP_TTL      = 300   # seconds (5 minutes)
    MAX_ATTEMPTS = 5

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route("/health")
    def health():
        """Health check: verifies kwtSMS credentials."""
        ok, balance, error = get_sms().verify()
        if ok:
            return jsonify({"ok": True, "balance": balance})
        return jsonify({"ok": False, "error": error}), 503

    @app.post("/otp/send")
    def otp_send():
        """
        Send an OTP to a phone number.

        POST /otp/send
        Content-Type: application/json
        Body: {"phone": "96598765432"}

        Returns:
            200: {"ok": true}
            400: {"error": "Phone number is required"}
            500: {"error": "Could not send code. Try again."}
        """
        data  = request.get_json(silent=True) or {}
        phone = str(data.get("phone", "")).strip()

        if not phone:
            return jsonify({"error": "Phone number is required"}), 400

        code = str(secrets.randbelow(1_000_000)).zfill(6)

        result = get_sms().send(phone, f"Your verification code is: {code}. Valid for 5 minutes.")

        if result["result"] != "OK":
            # Log the error server-side, but never expose raw API codes to clients
            app.logger.error("kwtSMS send failed: %s", result)
            return jsonify({"error": "Could not send verification code. Try again."}), 500

        _otp_store[phone] = {
            "code":     code,
            "expires":  time.time() + OTP_TTL,
            "attempts": 0,
        }

        return jsonify({"ok": True})

    @app.post("/otp/verify")
    def otp_verify():
        """
        Verify an OTP.

        POST /otp/verify
        Content-Type: application/json
        Body: {"phone": "96598765432", "code": "123456"}

        Returns:
            200: {"ok": true}  or  {"ok": false, "error": "..."}
        """
        data  = request.get_json(silent=True) or {}
        phone = str(data.get("phone", "")).strip()
        code  = str(data.get("code", "")).strip()

        entry = _otp_store.get(phone)

        if not entry:
            return jsonify({"ok": False, "error": "No code found. Request a new one."})

        if time.time() > entry["expires"]:
            del _otp_store[phone]
            return jsonify({"ok": False, "error": "Code expired. Request a new one."})

        if entry["attempts"] >= MAX_ATTEMPTS:
            del _otp_store[phone]
            return jsonify({"ok": False, "error": "Too many attempts. Request a new code."})

        if entry["code"] != code:
            _otp_store[phone]["attempts"] += 1
            return jsonify({"ok": False, "error": "Incorrect code."})

        del _otp_store[phone]
        return jsonify({"ok": True})

    @app.post("/sms/send")
    def sms_send():
        """
        Send an arbitrary SMS (admin/server use only).

        POST /sms/send
        Content-Type: application/json
        Body: {"phone": "96598765432", "message": "Hello!", "sender": "MY-BRAND"}

        Protect this endpoint with authentication in production.
        """
        data    = request.get_json(silent=True) or {}
        phone   = str(data.get("phone",   "")).strip()
        message = str(data.get("message", "")).strip()
        sender  = data.get("sender") or None

        if not phone or not message:
            return jsonify({"error": "phone and message are required"}), 400

        result = get_sms().send(phone, message, sender=sender)

        if result["result"] == "OK":
            return jsonify({
                "ok":             True,
                "msg_id":         result.get("msg-id"),
                "points_charged": result.get("points-charged"),
                "balance_after":  result.get("balance-after"),
            })

        return jsonify({
            "ok":    False,
            "code":  result.get("code"),
            "error": result.get("description"),
        }), 500

    return app


# ── Run as standalone development server ─────────────────────────────────────

if __name__ == "__main__":
    if not _flask_available:
        raise SystemExit("Install Flask first: pip install flask")

    app = create_app()
    print("Starting Flask dev server at http://127.0.0.1:5000")
    print("Endpoints:")
    print("  GET  /health       (verify credentials)")
    print("  POST /otp/send     (send OTP)")
    print("  POST /otp/verify   (verify OTP)")
    print("  POST /sms/send     (send arbitrary SMS)")
    app.run(debug=True)
