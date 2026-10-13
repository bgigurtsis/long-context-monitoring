"""Bounded-input validation shared by the CLI and the loopback HTTP service.

Every value that crosses a trust boundary (CLI argv, HTTP request bodies)
passes through here first. Limits are deliberately small: this service only
ever needs short identifiers, RFC-bounded email addresses, and short-lived
tokens.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .errors import ValidationError

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{1,24}$")

MAX_EMAIL_LENGTH = 320
MAX_IDENTIFIER_LENGTH = 64
MAX_TOKEN_LENGTH = 128
MAX_DISPLAY_NAME_LENGTH = 128
MAX_APPROVAL_REQUEST_IDS = 500

DECISIONS = ("previewed", "approved", "rejected")


def validate_identifier(label: str, value: object) -> str:
    """Validate an organization/account/operator/decision/batch id."""

    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    if not IDENTIFIER_RE.match(value):
        raise ValidationError(
            f"{label} must be 1-{MAX_IDENTIFIER_LENGTH} characters of "
            "letters, digits, '.', '_', or '-', starting with a letter or digit"
        )
    return value


def validate_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("email must be a string")
    if len(value) > MAX_EMAIL_LENGTH:
        raise ValidationError(f"email must be at most {MAX_EMAIL_LENGTH} characters")
    if not EMAIL_RE.match(value):
        raise ValidationError("email is not a valid address")
    return value


def validate_decision(value: object) -> str:
    if value not in DECISIONS:
        raise ValidationError(f"decision must be one of {', '.join(DECISIONS)}")
    return value  # type: ignore[return-value]


def validate_token(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError("token must be a non-empty string")
    if len(value) > MAX_TOKEN_LENGTH:
        raise ValidationError(f"token must be at most {MAX_TOKEN_LENGTH} characters")
    return value


def validate_ttl_seconds(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("recovery_ttl_seconds must be a positive integer")
    if value <= 0:
        raise ValidationError("recovery_ttl_seconds must be a positive integer")
    return value


def validate_age_range(min_age_seconds: object, max_age_seconds: object) -> tuple[int, int]:
    for label, value in (("min_age_seconds", min_age_seconds), ("max_age_seconds", max_age_seconds)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(f"{label} must be a non-negative integer")
        if value < 0:
            raise ValidationError(f"{label} must be a non-negative integer")
    if min_age_seconds > max_age_seconds:
        raise ValidationError("min_age_seconds must be less than or equal to max_age_seconds")
    return min_age_seconds, max_age_seconds  # type: ignore[return-value]


def validate_request_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError("request_ids must be a list of strings")
    if not value:
        raise ValidationError("request_ids must be a non-empty list")
    if len(value) > MAX_APPROVAL_REQUEST_IDS:
        raise ValidationError(f"request_ids must contain at most {MAX_APPROVAL_REQUEST_IDS} entries")
    validated: list[str] = []
    seen: set[str] = set()
    for item in value:
        request_id = validate_identifier("request_ids[]", item)
        if request_id in seen:
            raise ValidationError(f"duplicate request id in request_ids: {request_id}")
        seen.add(request_id)
        validated.append(request_id)
    return tuple(validated)


def validate_display_name(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("display_name must be a non-empty string")
    if len(value) > MAX_DISPLAY_NAME_LENGTH:
        raise ValidationError(f"display_name must be at most {MAX_DISPLAY_NAME_LENGTH} characters")
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
