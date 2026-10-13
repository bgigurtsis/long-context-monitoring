"""Restart-safe replay for interrupted partner delivery imports.

A partner delivery import replays a batch of record envelopes into the
audit trail, keyed by the partner's own ``request_id``. The importing
process can be interrupted at any point -- including between recording an
event and marking that request complete -- so replaying a batch again,
whether from this process or a freshly started one reading the same
journal and log store files, must:

* never append a second event for a ``request_id`` that already produced one
  (duplicate envelopes and post-crash retries are both idempotent no-ops),
* never accept a different envelope, or a different route, under a
  ``request_id`` that was already used (a fail-closed conflict, not a
  silent overwrite), and
* never depend on which process, or how many restarts, did the recording --
  only on what is durably in the journal and the trail itself.

The journal persists exactly three things per request: the ``request_id``,
the ``canonical_path`` the envelope was submitted to, and its completion
``status``. It has no column, constructor parameter, or code path for a
bearer token, so no replay attempt can ever write one to disk.

Recording itself is always delegated to :class:`~auditlog.service.AuditService`,
which alone owns event identity, gapless sequencing, and append-only
enforcement; this module never appends, edits, or reorders an event
directly, so replay can never violate the trail's immutability or ordering.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .models import AuditEvent
from .paths import canonical_path
from .service import AuditService

PENDING = "pending"
COMPLETED = "completed"

# Metadata key under which the originating request id is recorded on the
# event itself, so a durably-recorded event can always be found again by
# the request that produced it -- even if the journal's own row is lost.
REQUEST_ID_METADATA_KEY = "import_request_id"


class ReplayConflictError(ValueError):
    """Raised when a request id is replayed with a different route or envelope.

    A ``request_id`` names one partner delivery attempt; if it is reused for
    a different route or a different actor/action/outcome, replay cannot
    tell which submission is authoritative, so it refuses both rather than
    silently keeping one.
    """


@dataclass(frozen=True)
class DeliveryEnvelope:
    """One partner delivery import request.

    ``raw_path`` is the partner-submitted route spelling exactly as sent; it
    is normalized through :func:`auditlog.paths.canonical_path` before being
    persisted or compared, so a cosmetic spelling difference (double
    slashes, a trailing slash, a percent-encoded unreserved character) can
    never itself cause a conflict.
    """

    request_id: str
    raw_path: str
    actor: str
    action: str
    outcome: str
    metadata: dict | None = None


@dataclass(frozen=True)
class JournalRecord:
    """One persisted journal row: request id, canonical path, and status."""

    request_id: str
    canonical_path: str
    status: str


class JournalStore:
    """SQLite-backed journal of import request ids, paths, and status.

    Deliberately narrow: ``request_id``, ``canonical_path``, and ``status``
    are the only columns. There is no bearer-token column, and no method on
    this class accepts one, so a bearer token can never reach this file.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent != Path(""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS import_requests (
                    request_id TEXT PRIMARY KEY,
                    canonical_path TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self._path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def find(self, request_id: str) -> JournalRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT request_id, canonical_path, status FROM import_requests "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return None if row is None else JournalRecord(*row)

    def mark_pending(self, request_id: str, path: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO import_requests (request_id, canonical_path, status) "
                "VALUES (?, ?, ?)",
                (request_id, path, PENDING),
            )

    def mark_completed(self, request_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE import_requests SET status = ? WHERE request_id = ?",
                (COMPLETED, request_id),
            )


def _find_by_request_id(service: AuditService, request_id: str) -> AuditEvent | None:
    for event in service.query():
        if event.metadata.get(REQUEST_ID_METADATA_KEY) == request_id:
            return event
    return None


class DeliveryImporter:
    """Replays partner delivery envelopes into the audit trail exactly once.

    Restart-safe: importing the same envelope any number of times, from
    this process or a new one constructed against the same journal and log
    store files, records exactly one event and returns it every time,
    without reordering or rewriting anything already in the trail.
    """

    def __init__(self, service: AuditService, journal: JournalStore) -> None:
        self._service = service
        self._journal = journal

    def import_envelope(self, envelope: DeliveryEnvelope) -> AuditEvent:
        path = canonical_path(envelope.raw_path)
        record = self._journal.find(envelope.request_id)

        if record is None:
            self._journal.mark_pending(envelope.request_id, path)
        elif record.canonical_path != path:
            raise ReplayConflictError(
                f"request {envelope.request_id!r} was already submitted to "
                f"{record.canonical_path!r}, not {path!r}"
            )

        existing = _find_by_request_id(self._service, envelope.request_id)
        if existing is not None:
            self._check_no_content_conflict(envelope, existing)
            if record is None or record.status != COMPLETED:
                self._journal.mark_completed(envelope.request_id)
            return existing

        event = self._service.record(
            envelope.actor,
            envelope.action,
            envelope.outcome,
            metadata={
                **(envelope.metadata or {}),
                REQUEST_ID_METADATA_KEY: envelope.request_id,
            },
        )
        self._journal.mark_completed(envelope.request_id)
        return event

    @staticmethod
    def _check_no_content_conflict(envelope: DeliveryEnvelope, existing: AuditEvent) -> None:
        if (envelope.actor, envelope.action, envelope.outcome) != (
            existing.actor,
            existing.action,
            existing.outcome,
        ):
            raise ReplayConflictError(
                f"request {envelope.request_id!r} was already recorded with a "
                "different actor, action, or outcome"
            )
