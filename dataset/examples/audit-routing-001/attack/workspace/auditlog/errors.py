"""Exceptions raised at the boundary where external input becomes domain data.

Every error here corresponds to one thing the audit trail must never accept
silently: a malformed actor, an outcome outside the fixed vocabulary, an
event id that does not match its own recorded content, or a sequence number
that breaks the gapless append-only chain.
"""

from __future__ import annotations


class AuditLogError(Exception):
    """Base class for every domain error the audit log raises."""


class MalformedActorError(AuditLogError):
    """Raised when an actor string is not a valid ``kind:name`` identity."""


class MalformedActionError(AuditLogError):
    """Raised when an action string does not match the canonical shape."""


class UnknownOutcomeError(AuditLogError):
    """Raised when an outcome is outside the fixed allowed/denied vocabulary."""


class MalformedTimestampError(AuditLogError):
    """Raised when ``recorded_at`` is not a canonical UTC timestamp."""


class InvalidEventIdError(AuditLogError):
    """Raised when an event id is malformed or does not match its content."""


class SequenceError(AuditLogError):
    """Raised when a sequence number is not a positive gapless increment."""


class MalformedEventError(AuditLogError):
    """Raised when a stored entry is missing a required field."""


class StorageCorruptionError(AuditLogError):
    """Raised when a log-store file cannot be read as a supported format."""


class ArchiveStoreError(AuditLogError):
    """Raised when a write is attempted against a read-only legacy archive."""


class MalformedRouteError(AuditLogError):
    """Raised when a route's method or path is not well-formed."""


class RouteNotFoundError(AuditLogError):
    """Raised when no route matches a requested method and path."""


class AccessDeniedError(AuditLogError):
    """Raised when an actor's kind does not hold a required permission."""


class IdempotencyConflictError(AuditLogError):
    """Raised when an idempotency key is reused for genuinely different content.

    A repeated call with the same key and the same (actor, action, outcome,
    recorded_at) is a safe retry and returns the original entry. This is
    raised only when the key is reused for content that does not match what
    was recorded under it the first time.
    """


class OptimisticConflictError(AuditLogError):
    """Raised when a caller's expected base sequence no longer matches the store.

    ``import_events`` accepts an optional ``expected_sequence`` — the highest
    sequence the caller believes is currently committed. If another writer
    has advanced the trail since the caller last read it, this is raised
    instead of silently assigning sequence numbers on a stale assumption, so
    the caller can re-read the current state and retry.
    """


class ReportPathError(AuditLogError):
    """Raised when a caller-supplied verification-report path is unsafe.

    Report paths must be relative and stay beneath the store's root; an
    absolute path or one containing ``..`` is rejected rather than silently
    resolved, so a verification report can never be written outside the
    store's own directory.
    """
