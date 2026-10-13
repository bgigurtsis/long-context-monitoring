"""Bounded input validation shared by the CLI and the loopback HTTP service.

Every value that can originate outside the process (CLI arguments, HTTP
request bodies) is checked here for shape and length before it reaches
storage or the recovery flow.
"""
from __future__ import annotations

import re

from .errors import ValidationError

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")

MAX_ID_LEN = 64
MAX_EMAIL_LEN = 254
MAX_TOKEN_LEN = 512


def validate_id(value: object, field_name: str) -> str:
    """Validate an organization_id or account_id: bounded, non-empty, safe charset."""

    if not isinstance(value, str) or not _ID_PATTERN.match(value):
        raise ValidationError(
            f"{field_name} must be 1-{MAX_ID_LEN} characters of letters, digits, '.', '_', or '-'"
        )
    return value


def validate_email(value: object, field_name: str = "email") -> str:
    """Validate an email address: bounded length and a minimal address shape."""

    if not isinstance(value, str) or len(value) > MAX_EMAIL_LEN or not _EMAIL_PATTERN.match(value):
        raise ValidationError(f"{field_name} must be a valid email address of at most {MAX_EMAIL_LEN} characters")
    return value


def validate_token(value: object, field_name: str = "token") -> str:
    """Validate a recovery token's shape: bounded, printable, non-empty."""

    if not isinstance(value, str) or not value or len(value) > MAX_TOKEN_LEN:
        raise ValidationError(f"{field_name} must be 1-{MAX_TOKEN_LEN} characters")
    if any(ch.isspace() for ch in value):
        raise ValidationError(f"{field_name} must not contain whitespace")
    return value
