"""Password hashing and signed opaque-token helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for the given password."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, candidate_hex = hash_password(password, salt)
    return hmac.compare_digest(candidate_hex, hash_hex)


def new_opaque_id(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)


def sign(secret: bytes, nbytes: int = 24) -> str:
    """Create a self-verifying opaque token: "<random>.<hmac>"."""
    random_part = secrets.token_urlsafe(nbytes)
    mac = hmac.new(secret, random_part.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{random_part}.{mac}"


def verify(token: str, secret: bytes) -> bool:
    """Check that a token produced by sign() has not been tampered with."""
    if not isinstance(token, str) or token.count(".") != 1:
        return False
    random_part, _, mac = token.partition(".")
    if not random_part or not mac:
        return False
    expected = hmac.new(secret, random_part.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)
