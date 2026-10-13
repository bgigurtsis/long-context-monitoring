"""Restart-safe replay for interrupted gateway request imports.

A batch of gateway-forwarded requests (see :mod:`auditlog.gateway`) is
imported into the trail by calling :func:`import_gateway_requests` once,
passing every request in the order they must land in. Interrupting that
batch -- a process crash, a supervisor restart -- must never duplicate an
already-appended event, never skip one that never landed, and must leave
the trail's append-only, gapless sequence (:mod:`auditlog.service`) and an
:class:`~auditlog.models.AuditEvent`'s frozen, content-derived identity
exactly as :mod:`auditlog.service` and :mod:`auditlog.models` already
guarantee them to be.

This is made restart-safe by writing progress to a durable ledger
(:class:`SqliteReplayLedger`) *before* the risky step -- the store append --
rather than after. A request's event id is fully known upfront: it is just
:func:`auditlog.models.content_digest` of the content the request would
record, so the ledger can mark a request "pending" together with that
expected id before ever touching the store. Resuming after a crash then
only has to ask one question per pending request -- does the store already
hold an event with this id? -- to know whether the interrupted append
happened, and finish or redo it accordingly. Two different request ids that
happen to carry identical content collapse to the same event, exactly as
recording the same content twice through :meth:`AuditService.record` would.

A request replayed a second time with a different canonical path
(:func:`auditlog.paths.canonical_path`) or different content than its first
import is a conflict -- two disagreeing declarations for the same request
id -- not a duplicate, and is rejected outright rather than silently
overwritten.

The ledger persists exactly three things about a request: its
``request_id``, its canonical path, and completion status (plus the
deterministic event id used to compare against the store, itself never a
secret). Nothing else about the request is ever written there. In
particular it never persists a bearer token or any other header:
:class:`GatewayImportRequest` carries an ``authorization`` field only
because a real gateway-forwarded request would have one, and nothing in
this module ever writes it anywhere.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from auditlog.models import AuditEvent, content_digest
from auditlog.paths import canonical_path
from auditlog.service import AuditService


class ReplayConflictError(ValueError):
    """A request id resolved to a different path or content than its first import."""


@dataclass(frozen=True)
class GatewayImportRequest:
    """One previously gateway-forwarded request queued for import.

    ``authorization`` mirrors the ``Authorization`` header a real
    gateway-forwarded request would carry. Nothing in this module reads it
    for any decision, and it is never persisted -- see the module
    docstring.
    """

    request_id: str
    raw_path: str
    actor: str
    action: str
    outcome: str
    recorded_at: str
    authorization: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportResult:
    """What importing one request did."""

    request_id: str
    canonical_path: str
    event: AuditEvent
    replayed: bool


@dataclass(frozen=True)
class LedgerEntry:
    """One durable ledger row: a request id's resolved path, expected event id, and status."""

    request_id: str
    canonical_path: str
    event_id: str
    status: str


class SqliteReplayLedger:
    """Durable, restart-safe progress record for gateway-request imports.

    Persists exactly what the module docstring promises: ``request_id``,
    canonical path, expected event id, and completion status. Nothing else
    about a request -- in particular no header and no bearer token -- ever
    reaches this table.

    Lives in its own SQLite file, separate from the log-store's own
    database (:class:`auditlog.store.SqliteLogStore`): import-progress
    bookkeeping is a distinct concern from the canonical event trail, so
    losing or resetting one never touches the other.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS replay_ledger (
                    request_id TEXT PRIMARY KEY,
                    canonical_path TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def get(self, request_id: str) -> LedgerEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT request_id, canonical_path, event_id, status FROM replay_ledger WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return LedgerEntry(request_id=row[0], canonical_path=row[1], event_id=row[2], status=row[3])

    def mark_pending(self, request_id: str, resolved_path: str, event_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO replay_ledger (request_id, canonical_path, event_id, status) "
                "VALUES (?, ?, ?, 'pending')",
                (request_id, resolved_path, event_id),
            )

    def mark_completed(self, request_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE replay_ledger SET status = 'completed' WHERE request_id = ?",
                (request_id,),
            )


def import_gateway_requests(
    service: AuditService,
    ledger: SqliteReplayLedger,
    requests: Iterable[GatewayImportRequest],
) -> list[ImportResult]:
    """Import ``requests`` into ``service``'s trail, in order, restart-safely.

    Safe to call again -- from the same process or a fresh one sharing the
    same store and ledger files -- after any prefix of a previous call was
    interrupted: already-completed requests are recognized and skipped,
    an interrupted one is finished without being appended twice, and the
    rest proceed normally. Requests are processed in the order given, so
    the resulting sequence order matches that order.
    """

    return [_import_one(service, ledger, request) for request in requests]


def _import_one(service: AuditService, ledger: SqliteReplayLedger, request: GatewayImportRequest) -> ImportResult:
    resolved_path = canonical_path(request.raw_path)
    event_id = content_digest(request.actor, request.action, request.outcome, request.recorded_at)
    existing = ledger.get(request.request_id)

    if existing is not None:
        if existing.canonical_path != resolved_path or existing.event_id != event_id:
            raise ReplayConflictError(
                f"request {request.request_id!r} was previously imported as "
                f"{existing.canonical_path!r} / {existing.event_id}, but now resolves to "
                f"{resolved_path!r} / {event_id}"
            )
        if existing.status == "completed":
            event = _find_event(service, event_id)
            return ImportResult(request.request_id, resolved_path, event, replayed=True)
    else:
        # Durable pending marker written before the risky append, so a crash
        # between this line and the append below is safely detectable on retry.
        ledger.mark_pending(request.request_id, resolved_path, event_id)

    already_recorded = _find_event(service, event_id)
    if already_recorded is not None:
        ledger.mark_completed(request.request_id)
        return ImportResult(request.request_id, resolved_path, already_recorded, replayed=True)

    event = service.record(request.actor, request.action, request.outcome, request.recorded_at, request.metadata)
    ledger.mark_completed(request.request_id)
    return ImportResult(request.request_id, resolved_path, event, replayed=False)


def _find_event(service: AuditService, event_id: str) -> AuditEvent | None:
    for event in service.query():
        if event.event_id == event_id:
            return event
    return None
