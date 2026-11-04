import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, time as datetime_time, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet, InvalidToken

from backend.database.connection import (
    get_kite_session,
    save_kite_session,
)

SANDBOX_API_KEY = "sandboxdemo"
SANDBOX_API_SECRET = "sandboxdemo-secret"
SANDBOX_ROOT = "https://sandbox.kite.trade"
LIVE_ROOT = "https://api.kite.trade"
SANDBOX_LOGIN_URL = f"{SANDBOX_ROOT}/connect/login"
KITE_SESSION_COOKIE = "kite_session"
KITE_OAUTH_COOKIE = "kite_oauth_state"
KITE_CALLBACK_PATH = "/api/kite/sandbox/callback"
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _master_key() -> bytes:
    key = os.getenv("KITE_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("KITE_TOKEN_ENCRYPTION_KEY is required for Kite sessions.")
    try:
        decoded = base64.urlsafe_b64decode(key.encode("ascii"))
        if len(decoded) != 32:
            raise ValueError("Fernet keys must decode to 32 bytes.")
        return decoded
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("KITE_TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def _purpose_key(purpose: bytes) -> bytes:
    return hmac.new(_master_key(), b"zerodha-ai-intelligence:" + purpose, hashlib.sha256).digest()


def encrypt_access_token(access_token: str) -> str:
    return Fernet(base64.urlsafe_b64encode(_master_key())).encrypt(
        access_token.encode("utf-8")
    ).decode("ascii")


def decrypt_access_token(encrypted_access_token: str) -> str:
    try:
        return Fernet(base64.urlsafe_b64encode(_master_key())).decrypt(
            encrypted_access_token.encode("ascii")
        ).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise RuntimeError("Stored Kite access token could not be decrypted.") from exc


def _encode_signed_payload(payload: dict[str, Any], purpose: bytes) -> str:
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=")
    signature = hmac.new(_purpose_key(purpose), body, hashlib.sha256).digest()
    return b".".join(
        (body, base64.urlsafe_b64encode(signature).rstrip(b"="))
    ).decode("ascii")


def _decode_signed_payload(token: str, purpose: bytes) -> dict[str, Any] | None:
    try:
        body, signature = token.encode("ascii").split(b".", 1)
        expected = hmac.new(_purpose_key(purpose), body, hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature + b"=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            return None
        decoded = base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4))
        payload = json.loads(decoded)
        if not isinstance(payload, dict) or float(payload.get("exp", 0)) <= time.time():
            return None
        return payload
    except (ValueError, UnicodeEncodeError, json.JSONDecodeError):
        return None


def create_oauth_state() -> str:
    return _encode_signed_payload(
        {"nonce": secrets.token_urlsafe(32), "exp": time.time() + 600},
        b"oauth-state",
    )


def validate_oauth_state(state: str | None, cookie_state: str | None) -> bool:
    if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        return False
    payload = _decode_signed_payload(state, b"oauth-state")
    return bool(payload and payload.get("nonce"))


def sandbox_login_url(state: str) -> str:
    redirect_params = urlencode({"state": state})
    return f"{SANDBOX_LOGIN_URL}?{urlencode({'v': '3', 'api_key': SANDBOX_API_KEY, 'redirect_params': redirect_params})}"


def sandbox_redirect_url() -> str:
    return os.getenv(
        "KITE_SANDBOX_REDIRECT_URL",
        f"http://127.0.0.1:8000{KITE_CALLBACK_PATH}",
    )


def kite_expiry_at(now: datetime | None = None) -> datetime:
    local_now = (now or datetime.now(timezone.utc)).astimezone(INDIA_TZ)
    expiry = datetime.combine(local_now.date(), datetime_time(6, 0), tzinfo=INDIA_TZ)
    if local_now >= expiry:
        expiry += timedelta(days=1)
    return expiry.astimezone(timezone.utc)


def create_session_cookie(user_id: str, expires_at: datetime) -> str:
    return _encode_signed_payload(
        {"user_id": user_id, "environment": "sandbox", "exp": expires_at.timestamp()},
        b"browser-session",
    )


def get_session_user_id(cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    payload = _decode_signed_payload(cookie_value, b"browser-session")
    if not payload or payload.get("environment") != "sandbox":
        return None
    user_id = payload.get("user_id")
    return user_id if isinstance(user_id, str) and user_id else None


def persist_sandbox_session(user_id: str, access_token: str) -> datetime:
    expires_at = kite_expiry_at()
    encrypted_token = encrypt_access_token(access_token)
    save_kite_session(user_id, "sandbox", encrypted_token, expires_at)
    return expires_at


def get_access_token_for_user(user_id: str, environment: str) -> tuple[str | None, str]:
    session = get_kite_session(user_id, environment)
    if session is None:
        return None, "not_connected"

    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return None, "reconnect_needed"

    return decrypt_access_token(session["encrypted_access_token"]), "connected"
