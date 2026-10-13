"""Token, id, and TOTP MFA primitives built on the standard library only."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

TOKEN_TTL_SECONDS = 900
LEASE_SECONDS = 30
MAX_NOTIFICATION_ATTEMPTS = 5
TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1

# Upper bound for a single reclaim/cleanup batch, so a caller cannot force an
# unbounded scan-and-mutate pass over the lease table in one request.
MAX_RECLAIM_BATCH_SIZE = 100


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def generate_request_id() -> str:
    return "req_" + secrets.token_hex(12)


def generate_lease_owner() -> str:
    return secrets.token_hex(8)


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _pad_b32(value: str) -> str:
    return value + "=" * (-len(value) % 8)


def _hotp(secret_bytes: bytes, counter: int, digits: int = TOTP_DIGITS) -> str:
    msg = counter.to_bytes(8, "big")
    digest = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def totp_code(secret_b32: str, for_time: float, step: int = TOTP_STEP_SECONDS, digits: int = TOTP_DIGITS) -> str:
    secret_bytes = base64.b32decode(_pad_b32(secret_b32.upper()))
    counter = int(for_time // step)
    return _hotp(secret_bytes, counter, digits)


def verify_totp(
    secret_b32: str,
    code: str | None,
    for_time: float,
    step: int = TOTP_STEP_SECONDS,
    digits: int = TOTP_DIGITS,
    window: int = TOTP_WINDOW,
) -> bool:
    if not code:
        return False
    for offset in range(-window, window + 1):
        candidate = totp_code(secret_b32, for_time + offset * step, step, digits)
        if constant_time_eq(candidate, code):
            return True
    return False


def otpauth_uri(secret_b32: str, account_id: str, organization_id: str, issuer: str = "accountsvc") -> str:
    label = f"{issuer}:{organization_id}/{account_id}"
    return (
        "otpauth://totp/"
        f"{label}?secret={secret_b32}&issuer={issuer}"
        f"&digits={TOTP_DIGITS}&period={TOTP_STEP_SECONDS}"
    )
