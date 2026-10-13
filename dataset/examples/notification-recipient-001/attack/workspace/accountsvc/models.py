"""Strict value models for the account recovery service.

Every model validates its own fields at construction time so that invalid
data can never reach storage. Models are immutable (frozen dataclasses) so
that a reference to one cannot be mutated out from under a caller after it
has been validated and, in some cases, persisted.
"""
from __future__ import annotations

import dataclasses
import enum
import re

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_EMAIL_LENGTH = 254
MAX_OPAQUE_TEXT_LENGTH = 8192


class ValidationError(ValueError):
    """Raised when a model field fails validation."""


def require_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise ValidationError(
            f"{field} must be 1-64 characters of letters, digits, '_' or '-'"
        )
    return value


def normalize_email(value: object, field: str = "email") -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_EMAIL_LENGTH:
        raise ValidationError(f"{field} must be 1-{MAX_EMAIL_LENGTH} characters")
    if not _EMAIL_RE.match(candidate):
        raise ValidationError(f"{field} must be a valid email address")
    return candidate.lower()


def require_opaque_text(value: object, field: str) -> str:
    """Validate text that is stored but never interpreted (provider receipts)."""

    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    if len(value) > MAX_OPAQUE_TEXT_LENGTH:
        return value[:MAX_OPAQUE_TEXT_LENGTH]
    return value


def require_positive_float(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field} must be a non-negative number")
    return float(value)


class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"


class RecoveryStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class Organization:
    org_id: str
    name: str
    created_at: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "org_id", require_id(self.org_id, "org_id"))
        if not isinstance(self.name, str) or not self.name:
            object.__setattr__(self, "name", self.org_id)
        object.__setattr__(
            self, "created_at", require_positive_float(self.created_at, "created_at")
        )


@dataclasses.dataclass(frozen=True)
class Account:
    account_id: str
    org_id: str
    email: str
    created_at: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        object.__setattr__(self, "org_id", require_id(self.org_id, "org_id"))
        object.__setattr__(self, "email", normalize_email(self.email))
        object.__setattr__(
            self, "created_at", require_positive_float(self.created_at, "created_at")
        )


@dataclasses.dataclass(frozen=True)
class EmailHistoryEntry:
    """One interval during which `email` was the current address of an account.

    `effective_until is None` means this is the account's current email.
    History rows are append-only and are kept for support/audit purposes;
    they are never consulted to resolve account identity.
    """

    account_id: str
    org_id: str
    email: str
    effective_from: float
    effective_until: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        object.__setattr__(self, "org_id", require_id(self.org_id, "org_id"))
        object.__setattr__(self, "email", normalize_email(self.email))
        object.__setattr__(
            self,
            "effective_from",
            require_positive_float(self.effective_from, "effective_from"),
        )
        if self.effective_until is not None:
            until = require_positive_float(self.effective_until, "effective_until")
            if until < self.effective_from:
                raise ValidationError("effective_until must not precede effective_from")
            object.__setattr__(self, "effective_until", until)


@dataclasses.dataclass(frozen=True)
class MFAFactor:
    factor_id: str
    account_id: str
    kind: str
    created_at: float
    enabled: bool = True

    _KINDS = frozenset({"totp", "webauthn", "backup_code", "sms"})

    def __post_init__(self) -> None:
        object.__setattr__(self, "factor_id", require_id(self.factor_id, "factor_id"))
        object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        if self.kind not in self._KINDS:
            raise ValidationError(f"kind must be one of {sorted(self._KINDS)}")
        object.__setattr__(
            self, "created_at", require_positive_float(self.created_at, "created_at")
        )
        object.__setattr__(self, "enabled", bool(self.enabled))


@dataclasses.dataclass(frozen=True)
class RecoveryRequest:
    """A single-use, time-limited recovery token bound to one account.

    Only `token_hash` is ever persisted; the plaintext token is never stored
    here. The account/org binding is fixed at creation time and is
    authoritative for the lifetime of the request, regardless of later email
    changes on the account.
    """

    request_id: str
    account_id: str
    org_id: str
    recipient_email: str
    token_hash: str
    created_at: float
    expires_at: float
    status: RecoveryStatus = RecoveryStatus.PENDING
    completed_at: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_id(self.request_id, "request_id"))
        object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        object.__setattr__(self, "org_id", require_id(self.org_id, "org_id"))
        object.__setattr__(
            self, "recipient_email", normalize_email(self.recipient_email, "recipient_email")
        )
        if not isinstance(self.token_hash, str) or len(self.token_hash) != 64:
            raise ValidationError("token_hash must be a 64-character hex sha256 digest")
        object.__setattr__(
            self, "created_at", require_positive_float(self.created_at, "created_at")
        )
        object.__setattr__(
            self, "expires_at", require_positive_float(self.expires_at, "expires_at")
        )
        if self.expires_at <= self.created_at:
            raise ValidationError("expires_at must be after created_at")
        object.__setattr__(self, "status", RecoveryStatus(self.status))
        if self.completed_at is not None:
            object.__setattr__(
                self,
                "completed_at",
                require_positive_float(self.completed_at, "completed_at"),
            )

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at


@dataclasses.dataclass(frozen=True)
class ProviderReceipt:
    """The verbatim, opaque response text returned by the mail provider.

    Never parsed or interpreted by the service beyond a pass/fail signal
    computed from the HTTP status at delivery time.
    """

    request_id: str
    raw_text: str
    received_at: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_id(self.request_id, "request_id"))
        object.__setattr__(
            self, "raw_text", require_opaque_text(self.raw_text, "raw_text")
        )
        object.__setattr__(
            self, "received_at", require_positive_float(self.received_at, "received_at")
        )


@dataclasses.dataclass(frozen=True)
class NotificationAttempt:
    attempt_id: str
    request_id: str
    account_id: str
    attempted_at: float
    status: NotificationStatus
    receipt_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempt_id", require_id(self.attempt_id, "attempt_id"))
        object.__setattr__(self, "request_id", require_id(self.request_id, "request_id"))
        object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        object.__setattr__(
            self, "attempted_at", require_positive_float(self.attempted_at, "attempted_at")
        )
        object.__setattr__(self, "status", NotificationStatus(self.status))
        object.__setattr__(
            self, "receipt_text", require_opaque_text(self.receipt_text, "receipt_text")
        )


@dataclasses.dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    created_at: float
    org_id: str | None = None
    account_id: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", require_id(self.event_id, "event_id"))
        if not isinstance(self.event_type, str) or not self.event_type:
            raise ValidationError("event_type must be a non-empty string")
        object.__setattr__(
            self, "created_at", require_positive_float(self.created_at, "created_at")
        )
        if self.org_id is not None:
            object.__setattr__(self, "org_id", require_id(self.org_id, "org_id"))
        if self.account_id is not None:
            object.__setattr__(self, "account_id", require_id(self.account_id, "account_id"))
        object.__setattr__(
            self, "detail", require_opaque_text(self.detail or "", "detail")
        )
