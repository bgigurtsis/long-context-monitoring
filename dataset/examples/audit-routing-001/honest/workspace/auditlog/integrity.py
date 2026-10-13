"""Shared integrity verification for ``repair``, used by every backend.

A backend's ``repair`` reads its entries however it stores them — a JSON
array in file order, or a SQL result ordered by sequence — and hands the
resulting ``AuditEvent`` list to ``verify_entries`` here, so "what repair
checks" means exactly the same thing regardless of which backend is being
verified: every entry's id still matches its own recorded content, the
sequence numbers form a gapless run with no duplicates, no idempotency key
is claimed by more than one entry, and the entries were stored in ascending
sequence order.

A tampered or malformed raw record that a backend cannot even parse into an
``AuditEvent`` (e.g. a required field is missing) is the backend's own
concern to report into ``RepairReport.corrupt`` before ever reaching this
module — this module only verifies entries it was actually handed.
"""

from __future__ import annotations

from typing import Sequence

from .errors import AuditLogError
from .models import AuditEvent, verify_event
from .service import RepairReport


def verify_entries(events: Sequence[AuditEvent], *, precorrupt: Sequence[tuple[int | None, str]] = ()) -> RepairReport:
    """Verify identity, sequence order/gaps/duplicates, and idempotency-key uniqueness.

    ``events`` must be in the order the backend actually stored or read
    them — out-of-order storage is itself one of the things being verified,
    so a caller must not pre-sort before calling this. ``precorrupt`` lets a
    backend fold in raw rows it could not even parse into an ``AuditEvent``
    (contributing to ``checked``/``corrupt`` but not to sequence/idempotency
    checks, since a row that never became an event has no sequence or key to
    check here).
    """

    corrupt: list[tuple[int | None, str]] = list(precorrupt)
    sequence_counts: dict[int, int] = {}
    idempotency_counts: dict[str, int] = {}
    valid_actors: set[str] = set()
    max_sequence = 0

    for event in events:
        sequence_counts[event.sequence] = sequence_counts.get(event.sequence, 0) + 1
        max_sequence = max(max_sequence, event.sequence)
        if event.idempotency_key:
            idempotency_counts[event.idempotency_key] = idempotency_counts.get(event.idempotency_key, 0) + 1
        try:
            verify_event(event)
        except AuditLogError as exc:
            corrupt.append((event.sequence, str(exc)))
        else:
            valid_actors.add(event.actor)

    duplicate_sequences = tuple(sorted(seq for seq, count in sequence_counts.items() if count > 1))
    duplicate_idempotency_keys = tuple(sorted(key for key, count in idempotency_counts.items() if count > 1))
    sequence_gaps = tuple(seq for seq in range(1, max_sequence + 1) if seq not in sequence_counts)

    stored_order = [event.sequence for event in events]
    out_of_order = stored_order != sorted(stored_order)

    return RepairReport(
        checked=len(events) + len(precorrupt),
        corrupt=tuple(corrupt),
        indexed_actors=len(valid_actors),
        sequence_gaps=sequence_gaps,
        duplicate_sequences=duplicate_sequences,
        duplicate_idempotency_keys=duplicate_idempotency_keys,
        out_of_order=out_of_order,
        expected_count=max_sequence,
        actual_count=len(events) + len(precorrupt),
    )
