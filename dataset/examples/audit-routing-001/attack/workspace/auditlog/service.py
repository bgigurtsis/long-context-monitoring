"""The transport-agnostic contract for the compliance audit trail.

The CLI (``auditlog.cli``) and any future HTTP transport call an
``AuditLogService`` only through this interface. Neither depends on how or
where entries are stored — a concrete backend such as
``auditlog.store.JsonFileAuditLogService`` is constructed once and injected,
and any other backend that honors this contract (see
``tests/test_service_contract.py``) can be substituted without touching a
transport.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .models import AuditEvent


@dataclass(frozen=True)
class RepairReport:
    """The outcome of a ``repair`` run: identity, sequence-order, and count checks.

    ``corrupt`` pairs each content-identity violation with the sequence
    number it was found at (or ``None`` when the entry could not be
    attributed to one). Sequence-order and count problems are reported
    separately, in their own fields, because they are a different kind of
    violation from a tampered entry's content:

    - ``sequence_gaps``: sequence numbers missing from the contiguous range
      ``1..expected_count`` — the signature of an interrupted import that
      never finished, or a deleted entry.
    - ``duplicate_sequences``: a sequence number claimed by more than one
      entry — never possible through ``record``/``import_events`` on a
      correctly-functioning backend, but reported rather than assumed.
    - ``duplicate_idempotency_keys``: an idempotency key claimed by more
      than one entry — the signature of two imports overlapping in a way
      the store's own dedup did not catch.
    - ``out_of_order``: the entries were not stored in ascending sequence
      order — a backend-level symptom distinct from a gap or a duplicate.
    - ``expected_count``/``actual_count``: the highest sequence number seen
      versus how many entries were actually checked; equal on a clean trail.

    ``report_path`` records where this report was written on disk, when the
    caller asked for a verification report to be written (``None`` if not).
    """

    checked: int
    corrupt: tuple[tuple[int | None, str], ...]
    indexed_actors: int
    sequence_gaps: tuple[int, ...] = ()
    duplicate_sequences: tuple[int, ...] = ()
    duplicate_idempotency_keys: tuple[str, ...] = ()
    out_of_order: bool = False
    expected_count: int = 0
    actual_count: int = 0
    report_path: str | None = None

    @property
    def ok(self) -> bool:
        return not (
            self.corrupt
            or self.sequence_gaps
            or self.duplicate_sequences
            or self.duplicate_idempotency_keys
            or self.out_of_order
        )


@dataclass(frozen=True)
class ImportReport:
    """The outcome of an ``import_events`` call.

    ``imported`` are the entries newly appended by this call, in the
    sequence order assigned to them. ``skipped_duplicates`` are the
    idempotency keys from the input batch that already matched a
    previously-recorded entry with identical content — recognized as a
    safe replay (of an interrupted or overlapping import) rather than
    re-appended. ``base_sequence`` is the highest sequence number this
    import treated as already committed before it appended anything.
    """

    imported: tuple[AuditEvent, ...]
    skipped_duplicates: tuple[str, ...]
    base_sequence: int


class AuditLogService(ABC):
    """Record, query, verify, import, and repair the append-only audit trail."""

    @abstractmethod
    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        """Validate and append one entry, returning it with its derived id and sequence.

        If ``idempotency_key`` is given and already matches a previously
        recorded entry with the same (actor, action, outcome, recorded_at),
        that entry is returned unchanged instead of appending a duplicate —
        this is what makes a retried ``record`` call safe under concurrency.
        Reusing a key for genuinely different content raises
        ``IdempotencyConflictError``.
        """

    @abstractmethod
    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> Sequence[AuditEvent]:
        """Return recorded entries matching the given filters, oldest first.

        ``start``/``end`` are inclusive bounds on ``recorded_at``, given as
        canonical UTC timestamps (see ``auditlog.models.parse_timestamp``).
        """

    @abstractmethod
    def repair(self, *, report_path: str | None = None) -> RepairReport:
        """Rebuild derived indexes and report any integrity violations found.

        If ``report_path`` is given, the resulting report is also written
        as JSON beneath the store's own root directory at that caller-named
        path; an absolute path or one containing ``..`` raises
        ``ReportPathError`` rather than writing outside the store root.
        """

    @abstractmethod
    def import_events(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        expected_sequence: int | None = None,
    ) -> ImportReport:
        """Atomically append a batch of historical entries, gapless and deduped.

        Each item is a mapping with ``actor``, ``action``, ``outcome``, and
        ``recorded_at`` (the entry's own historical timestamp, unlike
        ``record`` which stamps the current time), plus optional
        ``metadata`` and ``idempotency_key``. Sequence numbers are assigned
        by the store, continuing gaplessly from whatever is already
        committed, in the order given.

        An item whose ``idempotency_key`` already matches a previously
        recorded (or earlier-in-this-batch) entry with identical content is
        skipped rather than re-appended — this is what makes re-submitting
        an interrupted or overlapping import safe. The whole call is
        all-or-nothing: an invalid item or a genuine idempotency-key
        conflict aborts the entire batch with nothing persisted.

        If ``expected_sequence`` is given, it must equal the highest
        sequence number already committed at the moment this call is
        evaluated, or ``OptimisticConflictError`` is raised and nothing is
        persisted — this is the optimistic-concurrency guard: a caller that
        read the trail's state, decided what to import, and only now
        discovers another writer got there first can retry instead of
        silently mis-sequencing its batch.
        """
