"""Strict domain models for the account recovery service.

Every model validates its fields at construction time so that invalid data
can never reach storage. Provider delivery receipts are modeled as opaque
text: the service never parses or interprets their contents, only stores and
replays them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .errors import ValidationError

MAX_ID_LENGTH = 128
MAX_EMAIL_LENGTH = 254
MAX_OPAQUE_TEXT_LENGTH = 8192
MAX_AUDIT_DETAIL_LENGTH = 4096

_ID_ALLOWED = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


def validate_id(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    if not (1 <= len(value) <= MAX_ID_LENGTH):
        raise ValidationError(
            f"{field_name} must be between 1 and {MAX_ID_LENGTH} characters"
        )
    if not set(value) <= _ID_ALLOWED:
        raise ValidationError(
            f"{field_name} may only contain letters, digits, '_', '.', or '-'"
        )
    return value


def validate_email(value: str, field_name: str = "email") -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    if not (3 <= len(value) <= MAX_EMAIL_LENGTH):
        raise ValidationError(
            f"{field_name} must be between 3 and {MAX_EMAIL_LENGTH} characters"
        )
    if value.count("@") != 1:
        raise ValidationError(f"{field_name} must contain exactly one '@'")
    local, _, domain = value.partition("@")
    if not local or not domain:
        raise ValidationError(f"{field_name} is missing a local or domain part")
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValidationError(f"{field_name} has an invalid domain")
    if any(ch.isspace() for ch in value):
        raise ValidationError(f"{field_name} must not contain whitespace")
    return value


def validate_opaque_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    if len(value) > MAX_OPAQUE_TEXT_LENGTH:
        value = value[:MAX_OPAQUE_TEXT_LENGTH]
    return value


@dataclass(frozen=True)
class Organization:
    org_id: str
    created_at: str

    def __post_init__(self) -> None:
        validate_id(self.org_id, "org_id")
        if not self.created_at:
            raise ValidationError("created_at is required")


@dataclass(frozen=True)
class Account:
    account_id: str
    org_id: str
    current_email: str
    created_at: str

    def __post_init__(self) -> None:
        validate_id(self.account_id, "account_id")
        validate_id(self.org_id, "org_id")
        validate_email(self.current_email, "current_email")
        if not self.created_at:
            raise ValidationError("created_at is required")


@dataclass(frozen=True)
class EmailHistoryEntry:
    account_id: str
    org_id: str
    email: str
    effective_from: str
    effective_to: Optional[str]
    released: bool
    entry_id: Optional[int] = None

    def __post_init__(self) -> None:
        validate_id(self.account_id, "account_id")
        validate_id(self.org_id, "org_id")
        validate_email(self.email, "email")
        if not self.effective_from:
            raise ValidationError("effective_from is required")


@dataclass(frozen=True)
class MfaEnrollment:
    account_id: str
    method: str
    enrolled: bool
    updated_at: str

    def __post_init__(self) -> None:
        validate_id(self.account_id, "account_id")
        if self.method not in ("none", "totp"):
            raise ValidationError("method must be 'none' or 'totp'")
        if not self.updated_at:
            raise ValidationError("updated_at is required")


@dataclass(frozen=True)
class RecoveryRequest:
    request_id: str
    account_id: str
    org_id: str
    token_hash: str
    created_at: str
    expires_at: str
    used_at: Optional[str] = None
    # Retained so a failed delivery can retry with the exact original link
    # instead of minting a new token; never returned by any API response.
    token_plain: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValidationError("request_id is required")
        validate_id(self.account_id, "account_id")
        validate_id(self.org_id, "org_id")
        if len(self.token_hash) != 64:
            raise ValidationError("token_hash must be a sha256 hex digest")
        if not self.created_at or not self.expires_at:
            raise ValidationError("created_at and expires_at are required")
        if self.token_plain is not None and len(self.token_plain) < 16:
            raise ValidationError("token_plain must be at least 16 characters")

    @property
    def used(self) -> bool:
        return self.used_at is not None


@dataclass(frozen=True)
class ProviderDeliveryReceipt:
    """An opaque provider response. Contents are never parsed or interpreted."""

    raw_text: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "raw_text", validate_opaque_text(self.raw_text, "raw_text")
        )


@dataclass(frozen=True)
class NotificationAttempt:
    request_id: str
    account_id: str
    attempt_number: int
    sent_at: str
    endpoint: str
    success: bool
    receipt: ProviderDeliveryReceipt
    retry_locator: Optional[str] = None
    attempt_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValidationError("request_id is required")
        validate_id(self.account_id, "account_id")
        if self.attempt_number < 1:
            raise ValidationError("attempt_number must be >= 1")
        if not self.sent_at:
            raise ValidationError("sent_at is required")
        if not self.endpoint:
            raise ValidationError("endpoint is required")


@dataclass(frozen=True)
class PendingRetryAttempt:
    """A durable, restart-safe record of one request awaiting a mail retry.

    Rebuilt entirely from storage -- never from in-memory state -- so a
    freshly started process can resume retries exactly where a prior
    process left off.
    """

    request_id: str
    account_id: str
    token_plain: str
    retry_locator: str

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValidationError("request_id is required")
        validate_id(self.account_id, "account_id")
        if not self.token_plain:
            raise ValidationError("token_plain is required")
        if not self.retry_locator:
            raise ValidationError("retry_locator is required")


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    ts: str
    detail: str
    org_id: Optional[str] = None
    account_id: Optional[str] = None
    event_id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValidationError("event_type is required")
        if not self.ts:
            raise ValidationError("ts is required")
        object.__setattr__(
            self, "detail", validate_opaque_text(self.detail, "detail")[
                :MAX_AUDIT_DETAIL_LENGTH
            ]
        )
