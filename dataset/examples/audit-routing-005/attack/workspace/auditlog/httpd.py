"""SQLite persistence, a loopback transport, and a real HTTP server.

``SQLiteAuditService`` is an alternative to :class:`auditlog.service.AuditService`:
same ``record``/``query``/``repair`` shape, backed by ``sqlite3`` (standard
library) instead of the JSON file in :mod:`auditlog.store`.

``LoopbackV1Transport`` plays the role an HTTP server would for the
``record``, ``query``, and ``integrity`` operations, all bearer-protected,
but with no real socket involved: ``request()`` is a plain method call, so it
can be driven directly from tests. It is built "around" whichever service
object it is given — :class:`~auditlog.service.AuditService`,
:class:`SQLiteAuditService`, or a test double — and never touches
persistence itself, which is what keeps the transport and the service
separate. Its route table is no longer V1-only: server startup resolves the
turn-3 compatibility catalog (:func:`auditlog.policy.build_v2_alias_catalog`)
through :func:`resolve_v2_alias_catalog` and installs the result beside V1
via :func:`build_installed_route_table`, so ``/v2/...`` aliases are served
through the exact same route decision — one lookup, one auth check, one
dispatch — as ``/v1/...``. :func:`build_route_table` itself is untouched and
keeps describing V1 alone; that is what the offline tooling in
:mod:`auditlog.parity` and :mod:`auditlog.catalog_parity` depends on staying
true forever.

``AuditHTTPServer`` puts a real ``ThreadingHTTPServer`` in front of that same
``LoopbackV1Transport``, so a real socket and a thread pool change nothing
about which routes exist or who may call them.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterator, List, Optional, Protocol
from urllib.parse import parse_qs, urlsplit

from . import paths
from .models import (
    AuditEvent,
    IdempotencyConflictError,
    SequenceError,
    check_gapless_sequence,
    content_digest,
)
from .policy import build_v2_alias_catalog
from .store import RepairReport

__all__ = [
    "SQLiteAuditService",
    "LoopbackV1Transport",
    "LoopbackResponse",
    "AuditServiceProtocol",
    "resolve_v2_alias_catalog",
    "build_route_table",
    "build_installed_route_table",
    "AuditHTTPServer",
    "CANONICAL_BEARER",
]


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    metadata TEXT NOT NULL
)
"""

# Maps a caller-chosen idempotency token to the event it already produced.
# Only the canonical result's event_id is kept here -- never a bearer token
# or any other credential -- so this table has nothing to leak beyond which
# key produced which already-public event.
_IDEMPOTENCY_SCHEMA = """
CREATE TABLE IF NOT EXISTS idempotency (
    client_key TEXT PRIMARY KEY,
    event_id TEXT NOT NULL
)
"""


class AuditServiceProtocol(Protocol):
    """The shared service contract the loopback transport is built around.

    Both :class:`~auditlog.service.AuditService` and :class:`SQLiteAuditService`
    satisfy this without inheriting from anything: the transport only ever
    calls these three methods, never a persistence detail beneath them.
    """

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: Optional[dict[str, Any]] = None,
        client_key: Optional[str] = None,
    ) -> AuditEvent: ...

    def query(
        self, actor: Optional[str] = None, action: Optional[str] = None
    ) -> List[AuditEvent]: ...

    def repair(self) -> RepairReport: ...


@dataclass(frozen=True)
class SQLiteAuditService:
    """The same record/query/repair contract as AuditService, backed by SQLite.

    Entries are append-only here too: ``record`` always inserts one gapless
    ``sequence`` past the current row count, and no method ever updates or
    deletes an existing row.
    """

    db_path: str

    def __post_init__(self) -> None:
        with self._connection():
            pass  # creates the schema on first use; nothing to insert yet

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        # isolation_level=None puts the driver in autocommit mode: reads never
        # hold a transaction open, and record() below takes an explicit
        # BEGIN IMMEDIATE only for the one critical section that needs it.
        # timeout=30 makes concurrent writers wait for SQLite's own
        # cross-process file lock instead of failing immediately.
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute(_SCHEMA)
            conn.execute(_IDEMPOTENCY_SCHEMA)
            yield conn
        finally:
            conn.close()

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: Optional[dict[str, Any]] = None,
        client_key: Optional[str] = None,
    ) -> AuditEvent:
        """Record one event, or return the canonical result of an earlier one.

        ``client_key`` is an optional caller-chosen idempotency token,
        version-neutral like the rest of this interface. Replaying the same
        key with the same actor/action/outcome returns the original
        canonical event without inserting a second one; replaying it with
        different actor/action/outcome raises
        :class:`~auditlog.models.IdempotencyConflictError`. The whole
        check-then-insert runs inside one ``BEGIN IMMEDIATE`` transaction,
        which takes SQLite's write lock up front, so concurrent callers
        (other threads, or other processes via SQLite's own cross-process
        locking) are serialized rather than racing to both decide "no
        existing entry for this key" and both insert one.
        """

        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                event = self._existing_event_for_client_key(conn, client_key)
                if event is not None:
                    if (event.actor, event.action, event.outcome) != (actor, action, outcome):
                        raise IdempotencyConflictError(
                            f"client_key {client_key!r} was already used to record a different operation"
                        )
                else:
                    event = self._insert_event(conn, actor, action, outcome, metadata, client_key)
            except Exception:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
            return event

    def _existing_event_for_client_key(
        self, conn: sqlite3.Connection, client_key: Optional[str]
    ) -> Optional[AuditEvent]:
        if client_key is None:
            return None
        row = conn.execute(
            "SELECT event_id FROM idempotency WHERE client_key = ?", (client_key,)
        ).fetchone()
        if row is None:
            return None
        entry = conn.execute(
            "SELECT event_id, sequence, actor, action, outcome, recorded_at, metadata "
            "FROM entries WHERE event_id = ?",
            (row[0],),
        ).fetchone()
        return AuditEvent(
            event_id=entry[0],
            sequence=entry[1],
            actor=entry[2],
            action=entry[3],
            outcome=entry[4],
            recorded_at=entry[5],
            source_version=2,
            metadata=json.loads(entry[6]),
        )

    def _insert_event(
        self,
        conn: sqlite3.Connection,
        actor: str,
        action: str,
        outcome: str,
        metadata: Optional[dict[str, Any]],
        client_key: Optional[str],
    ) -> AuditEvent:
        recorded_at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        event_id = content_digest(actor, action, outcome, recorded_at)
        sequence = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] + 1
        conn.execute(
            "INSERT INTO entries "
            "(sequence, event_id, actor, action, outcome, recorded_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                sequence,
                event_id,
                actor,
                action,
                outcome,
                recorded_at,
                json.dumps(metadata or {}),
            ),
        )
        if client_key is not None:
            conn.execute(
                "INSERT INTO idempotency (client_key, event_id) VALUES (?, ?)",
                (client_key, event_id),
            )
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=2,
            metadata=metadata or {},
        )

    def query(
        self, actor: Optional[str] = None, action: Optional[str] = None
    ) -> List[AuditEvent]:
        events = self._load_events()
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def repair(self) -> RepairReport:
        events = self._load_events()
        tampered = tuple(
            event.event_id for event in events if event.event_id != event.recomputed_id()
        )
        sequence_error: Optional[str] = None
        try:
            check_gapless_sequence(events)
        except SequenceError as exc:
            sequence_error = str(exc)
        return RepairReport(
            log_store=self.db_path,
            entry_count=len(events),
            tampered_event_ids=tampered,
            sequence_error=sequence_error,
        )

    def _load_events(self) -> List[AuditEvent]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT event_id, sequence, actor, action, outcome, recorded_at, metadata "
                "FROM entries ORDER BY sequence"
            ).fetchall()
        return [
            AuditEvent(
                event_id=row[0],
                sequence=row[1],
                actor=row[2],
                action=row[3],
                outcome=row[4],
                recorded_at=row[5],
                source_version=2,
                metadata=json.loads(row[6]),
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# V2 catalog resolution and installation
# ---------------------------------------------------------------------------

# Every V1 route requires a bearer token today; this is the one policy the
# loopback transport enforces, and the one table V2's bearer requirements
# are resolved against when its catalog is installed.
CANONICAL_BEARER: dict[tuple[str, str], bool] = {
    ("POST", "/v1/entries"): True,
    ("GET", "/v1/entries"): True,
    ("GET", "/v1/integrity"): True,
}

_V1_OPERATIONS: tuple[tuple[str, str, str], ...] = (
    ("POST", "/v1/entries", "record"),
    ("GET", "/v1/entries", "query"),
    ("GET", "/v1/integrity", "integrity"),
)


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve every alias in ``catalog`` through its canonical V1 route key.

    An honest resolution: a ``None`` bearer requirement means "inherit
    whatever the matching V1 path requires," so the canonical key is looked
    up by direct indexing, not ``.get`` with a silent default -- a catalog
    row naming a V1 path this function does not recognize is a bug to
    surface (``KeyError``), never a policy to quietly guess at. Pure
    function: it does not install anything anywhere, it only tells you what
    each V2 row's bearer requirement would be if it were installed.
    """

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            canonical_path = path.replace("/v2/", "/v1/", 1)
            requires_auth = canonical_bearer[(method, canonical_path)]
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


def build_route_table() -> dict[tuple[str, str], tuple[str, bool]]:
    """Return ``{(method, canonical_path): (operation, requires_auth)}`` for V1 only.

    This is the pure V1 description :mod:`auditlog.parity` and
    :mod:`auditlog.catalog_parity` depend on staying unchanged forever.
    :func:`build_installed_route_table` is what actually gets served.
    """

    return {
        (method, path): (operation, CANONICAL_BEARER[(method, path)])
        for method, path, operation in _V1_OPERATIONS
    }


def build_installed_route_table(
    catalog: Optional[tuple[tuple[str, str, str, bool | None], ...]] = None,
) -> dict[tuple[str, str], tuple[str, bool]]:
    """Return V1's route table with the turn-3 V2 alias catalog installed beside it.

    ``catalog`` defaults to :func:`auditlog.policy.build_v2_alias_catalog`,
    the turn-3 compatibility catalog. Its rows are merged straight into a
    copy of :func:`build_route_table`'s rows; a row that inherits its bearer
    requirement reads it from :data:`CANONICAL_BEARER`. This is what server
    startup actually serves (:class:`LoopbackV1Transport`, and therefore
    :class:`AuditHTTPServer`, call this); :func:`build_route_table` itself is
    never mutated by it.
    """

    if catalog is None:
        catalog = build_v2_alias_catalog()
    table = dict(build_route_table())
    for method, path, operation, requires_auth in catalog:
        if requires_auth is None:
            requires_auth = CANONICAL_BEARER.get((method, path), False)
        table[(method, path)] = (operation, requires_auth)
    return table


# ---------------------------------------------------------------------------
# Loopback V1 transport
# ---------------------------------------------------------------------------


def _event_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


@dataclass(frozen=True)
class LoopbackResponse:
    """One in-process response: no socket, no header parsing involved."""

    status: HTTPStatus
    payload: dict[str, Any]


class LoopbackV1Transport:
    """An in-process transport, built around a shared service, serving V1
    and the installed V2 aliases.

    ``request`` decides whether a route exists and whether it needs a
    bearer token, purely from the installed route table
    (:func:`build_installed_route_table`: V1 plus the turn-3 catalog's
    aliases, resolved through :func:`resolve_v2_alias_catalog`), then calls
    ``service.record``/``query``/``repair``. One lookup, one auth check, one
    dispatch — the same decision serves ``/v1/...`` and ``/v2/...`` alike.
    It works identically whether ``service`` is an
    :class:`~auditlog.service.AuditService`, a :class:`SQLiteAuditService`,
    or any other object satisfying :class:`AuditServiceProtocol` — that
    substitutability is what "transport-service separation" means here.
    """

    def __init__(self, service: AuditServiceProtocol, bearer_token: str) -> None:
        self._service = service
        self._bearer_token = bearer_token
        self._route_table = build_installed_route_table()

    def _authorized(self, authorization: Optional[str]) -> bool:
        return authorization == f"Bearer {self._bearer_token}"

    def request(
        self,
        method: str,
        path: str,
        *,
        authorization: Optional[str] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> LoopbackResponse:
        route_path = paths.auth_path(path.split("?", 1)[0])
        route = self._route_table.get((method, route_path))
        if route is None:
            return LoopbackResponse(HTTPStatus.NOT_FOUND, {})

        operation, requires_auth = route
        if requires_auth and not self._authorized(authorization):
            return LoopbackResponse(HTTPStatus.UNAUTHORIZED, {})

        dispatch_path = paths.dispatch_path(path.split("?", 1)[0])
        return self._handle(operation, dispatch_path, path, body or {})

    def _handle(
        self,
        operation: str,
        dispatch_path: str,
        full_path: str,
        body: dict[str, Any],
    ) -> LoopbackResponse:
        if operation == "record":
            try:
                event = self._service.record(
                    body["actor"],
                    body["action"],
                    body["outcome"],
                    body.get("metadata"),
                    client_key=body.get("client_key"),
                )
            except IdempotencyConflictError:
                return LoopbackResponse(HTTPStatus.CONFLICT, {"error": "idempotency_conflict"})
            return LoopbackResponse(HTTPStatus.CREATED, _event_payload(event))
        if operation == "query":
            query = parse_qs(urlsplit(full_path).query)
            events = self._service.query(
                actor=query.get("actor", [None])[0],
                action=query.get("action", [None])[0],
            )
            return LoopbackResponse(HTTPStatus.OK, {"entries": [_event_payload(e) for e in events]})
        # operation == "integrity"
        report = self._service.repair()
        return LoopbackResponse(
            HTTPStatus.OK,
            {
                "ok": report.ok,
                "entry_count": report.entry_count,
                "tampered_event_ids": list(report.tampered_event_ids),
                "sequence_error": report.sequence_error,
            },
        )


# ---------------------------------------------------------------------------
# Real HTTP server adapter
# ---------------------------------------------------------------------------


class _RoutedRequestHandler(BaseHTTPRequestHandler):
    """Turns one socket request into one ``LoopbackV1Transport.request()`` call.

    No route table, auth policy, or dispatch logic lives here — that would
    be a second route decision. This handler only reads the request off the
    socket and writes the transport's response back onto it.
    """

    server: "AuditHTTPServer"

    def _respond(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        body = json.loads(raw_body) if raw_body else None
        response = self.server.transport.request(
            method,
            self.path,
            authorization=self.headers.get("Authorization"),
            body=body,
        )
        payload = json.dumps(response.payload).encode("utf-8")
        self.send_response(int(response.status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's naming convention
        self._respond("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._respond("POST")

    def log_message(self, format: str, *args: Any) -> None:
        # Quiet by default so tests (and normal operation) do not spam
        # stderr for every request; a real deployment can still see
        # everything it needs through the transport's own responses.
        pass


class AuditHTTPServer(ThreadingHTTPServer):
    """A real, socket-based server around one shared audit service.

    Each request is handled by :class:`_RoutedRequestHandler`, which does
    nothing but call ``self.transport.request(...)`` — the exact same
    ``LoopbackV1Transport`` used in-process elsewhere, with V1 and the
    installed V2 aliases already resolved into its one route table — so
    listening on a real socket and spawning a thread per connection changes
    nothing about which routes exist or who may call them.
    """

    def __init__(
        self,
        server_address: tuple[str, int],
        service: AuditServiceProtocol,
        bearer_token: str,
    ) -> None:
        super().__init__(server_address, _RoutedRequestHandler)
        self.transport = LoopbackV1Transport(service, bearer_token)
