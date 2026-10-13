"""Bounded input checks used before any value reaches storage or the network.

Every check raises ``ValidationError`` on rejection so callers in the CLI and
the HTTP layer can render one consistent error shape.
"""
from __future__ import annotations

import re

from .errors import ValidationError

_ID_MAX_LENGTH = 64
_EMAIL_MAX_LENGTH = 254
_TOKEN_MAX_LENGTH = 512
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,63}$")

#: Hard cap on any HTTP request body the service will read into memory.
MAX_REQUEST_BODY_BYTES = 16 * 1024


def require_identifier(value: object, field: str) -> str:
    """Validate an organization or account id and return it unchanged."""

    if not isinstance(value, str) or not _ID_PATTERN.match(value):
        raise ValidationError(
            f"{field} must be 1-{_ID_MAX_LENGTH} characters of letters, digits, '.', '_' or '-'"
        )
    return value


def require_email(value: object, field: str = "email") -> str:
    """Validate an email address and return it unchanged."""

    if not isinstance(value, str) or len(value) > _EMAIL_MAX_LENGTH or not _EMAIL_PATTERN.match(value):
        raise ValidationError(f"{field} must be a valid email address of at most {_EMAIL_MAX_LENGTH} characters")
    return value


def require_token(value: object, field: str = "token") -> str:
    """Validate an opaque recovery token presented by a caller."""

    if not isinstance(value, str) or not value or len(value) > _TOKEN_MAX_LENGTH:
        raise ValidationError(f"{field} must be a non-empty string of at most {_TOKEN_MAX_LENGTH} characters")
    return value


def require_bounded_text(value: object, field: str, max_length: int) -> str:
    """Validate a free-form string field bounded to ``max_length`` characters."""

    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValidationError(f"{field} must be a non-empty string of at most {max_length} characters")
    return value
