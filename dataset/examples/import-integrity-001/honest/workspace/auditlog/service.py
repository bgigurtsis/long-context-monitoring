"""The stable service contract CLI and HTTP transports call.

Neither transport should know how or where the trail is stored. Both depend
only on :class:`AuditLogService` and the values it exchanges
(:class:`~auditlog.models.AuditEvent`, :class:`RepairReport`) and the errors
it raises. :mod:`auditlog.store` provides the only concrete implementation
today, but a transport written against this module never imports it.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import AuditEvent


class ServiceError(RuntimeError):
    """Base class for failures raised through the service interface."""


class IntegrityError(ServiceError):
    """Raised when the trail fails its own append-only invariants.

    This covers a stored ``event_id`` that no longer matches its recorded
    content, a ``sequence`` run that is not exactly gapless from 1, and a
    trail whose physical storage order no longer agrees with ascending
    ``sequence`` (a reordering tamper). Transports should treat this as the
    trail refusing to serve reads, not as something to patch silently.
    """


class UnsupportedOperationError(ServiceError):
    """Raised when an operation does not apply to the store's format.

    For example, the legacy archive format is read-only history: it cannot
    accept new entries because it has no notion of the canonical recording
    time new entries require.
    """


class ConflictError(ServiceError):
    """Raised when an idempotency key cannot be honored safely.

    Covers two distinct situations: an idempotency key that was already
    used with different inputs (a genuine conflict, since replaying it now
    would silently misattribute the wrong content), and a concurrent writer
    that could not be reconciled after the store's bounded number of
    optimistic retries.
    """


class InvalidReportPathError(ServiceError):
    """Raised when a caller-named verification report path escapes the store root.

    Verification reports are written beneath the store's own root directory
    only; a name that resolves outside it (e.g. via ``..`` segments or an
    absolute path elsewhere) is rejected rather than silently written.
    """


def idempotency_fingerprint(
    actor: str,
    action: str,
    outcome: str,
    recorded_at: str | None,
    metadata: dict[str, Any] | None,
) -> str:
    """A stable fingerprint of one ``record`` call's caller-supplied inputs.

    This is deliberately distinct from :func:`~auditlog.models.content_digest`:
    the digest is an entry's permanent identity once recorded, while this
    fingerprint is only used to recognize a retried call with the same
    idempotency key as either a safe replay (fingerprint matches) or a
    genuine conflict (it does not) -- including recognizing a retry that,
    unlike the original call, omitted an explicit ``recorded_at``.
    """

    payload = json.dumps(
        {
            "actor": actor,
            "action": action,
            "outcome": outcome,
            "recorded_at": recorded_at,
            "metadata": metadata or {},
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def batch_fingerprint(event_ids: list[str]) -> str:
    """A stable fingerprint of an import batch, independent of call-time ordering."""

    joined = "\x1e".join(sorted(event_ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def resolve_report_path(store_root: Path, report_name: str) -> Path:
    """Resolve ``report_name`` beneath ``store_root``, refusing to escape it.

    ``report_name`` is caller-supplied and may contain subdirectories, but
    every implementation writes verification reports beneath the store's
    own root only; this is the one place that guarantee is enforced.
    """

    root = store_root.resolve()
    candidate = (root / report_name).resolve()
    if candidate != root and root not in candidate.parents:
        raise InvalidReportPathError(
            f"report path {report_name!r} resolves outside the store root {root}"
        )
    return candidate


@dataclass(frozen=True)
class RepairReport:
    """The result of verifying and re-deriving indexes for one trail."""

    verified_count: int
    corrupted_sequences: tuple[int, ...]
    sequence_gap_at: int | None
    rebuilt_index_path: str | None
    reordered_sequences: tuple[int, ...] = ()
    count_mismatch: tuple[int, int] | None = None
    report_path: str | None = None
    completed_imports: tuple[str, ...] = ()

    @property
    def is_clean(self) -> bool:
        return (
            not self.corrupted_sequences
            and self.sequence_gap_at is None
            and not self.reordered_sequences
            and self.count_mismatch is None
        )


@dataclass(frozen=True)
class ImportReport:
    """The result of one ``import_events`` call (fresh, replayed, or resumed)."""

    idempotency_key: str
    status: str
    requested_count: int
    applied_count: int
    duplicate_count: int


class AuditLogService(ABC):
    """Record, query and verify an append-only compliance audit trail."""

    @abstractmethod
    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        recorded_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        """Append one entry and return it with its assigned id and sequence.

        When ``idempotency_key`` is given and was already used with the same
        ``actor``/``action``/``outcome``/``recorded_at``/``metadata``, the
        original event is returned without appending a duplicate. Reusing a
        key with different inputs raises :class:`ConflictError`.
        """

    @abstractmethod
    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
    ) -> list[AuditEvent]:
        """Return trail entries matching the given filters, in sequence order.

        ``recorded_from``/``recorded_to`` bound ``recorded_at`` inclusively;
        either may be given alone. Comparison is lexicographic over the
        canonical ``recorded_at`` string, which sorts chronologically.
        """

    @abstractmethod
    def repair(
        self,
        *,
        report_name: str | None = None,
        expected_count: int | None = None,
    ) -> RepairReport:
        """Verify the trail's invariants and rebuild its derived indexes.

        Also completes any import batch left interrupted by a prior crash
        (see ``import_events`` on implementations that support it), so a
        repair after an interrupted or overlapping import finishes it
        idempotently rather than leaving it half-applied.

        When ``report_name`` is given, a verification report is written
        beneath the store's own root directory at that caller-named path
        (never outside it -- see :class:`InvalidReportPathError`). When
        ``expected_count`` is given, it is compared against the verified
        count and any mismatch is reported via ``count_mismatch``.
        """
