"""HTTP transport for the audit log: alias resolution, and the daemon.

`resolve_v2_alias_catalog` is the stable alias-resolution seam described
below. Everything past it is the actual network daemon: a bearer-protected
`record`/`query`/`integrity` API backed by SQLite persistence.
`ROUTE_ACTIONS` (mirroring `auditlog.policy.CANONICAL_V1_BEARER`) stays the
canonical, V1-only route mapping; `build_server` resolves the V2 alias
catalog in `auditlog.policy.build_v2_alias_catalog` through
`resolve_v2_alias_catalog` and installs the result alongside it, so every
protected `/v2/*` alias dispatches to the same handler as its canonical V1
route. Cohort phase (`load_cohort_configuration`) is recorded on the server
but never consulted for auth or handler selection -- installed routes and
their bearer requirements are the same for every caller regardless of
cohort.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from auditlog.paths import auth_path, dispatch_path
from auditlog.policy import CANONICAL_V1_BEARER, build_v2_alias_catalog
from auditlog.service import AuditLogService, IntegrityError, SequenceError


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve inherited aliases through their canonical V1 route keys.

    A `None` bearer requirement means "inherit the canonical V1 route's
    requirement", so its `(method, canonical_path)` key must already be in
    `canonical_bearer`. This is not a fallback: an alias naming a canonical
    route `canonical_bearer` doesn't have is a bug in the caller's catalog,
    not a case to silently default through.
    """

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            canonical_path = path.replace("/v2/", "/v1/", 1)
            requires_auth = canonical_bearer[(method, canonical_path)]
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


# The canonical V1-only route mapping. Keys match
# `auditlog.policy.CANONICAL_V1_BEARER` exactly: every V1 route has a
# canonical bearer requirement, and every canonical requirement names a
# route here. This stays V1-only on purpose -- `build_server` builds the
# actual dispatch table each server uses (V1 routes plus every resolved V2
# alias) from this constant, rather than mutating it.
ROUTE_ACTIONS: dict[tuple[str, str], str] = {
    ("POST", "/v1/entries"): "record",
    ("GET", "/v1/entries"): "query",
    ("GET", "/v1/integrity"): "integrity",
}


class SqliteEventStore:
    """SQLite-backed `EventStore` (see `auditlog.storage`).

    Unlike the CLI's single-writer JSON file, this store backs a daemon that
    may be read by several request threads -- and, for a separate OS process
    opening the same path, several processes -- at once. Autocommit mode plus
    WAL journaling means a writer's committed entry is immediately visible to
    any other connection that opens the same file afterward. Connections are
    kept one-per-thread because a `sqlite3.Connection` is not safe to share
    across threads.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        self._init_schema()

    def _connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, isolation_level=None, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        self._connection().execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                sequence INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                source_version INTEGER NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )

    def read_all(self) -> list[dict]:
        rows = self._connection().execute(
            "SELECT event_id, sequence, actor, action, outcome, recorded_at, "
            "source_version, metadata FROM entries ORDER BY sequence"
        ).fetchall()
        return [
            {
                "event_id": event_id,
                "sequence": sequence,
                "actor": actor,
                "action": action,
                "outcome": outcome,
                "recorded_at": recorded_at,
                "source_version": source_version,
                "metadata": json.loads(metadata),
            }
            for event_id, sequence, actor, action, outcome, recorded_at, source_version, metadata in rows
        ]

    def append(self, entry: dict) -> None:
        self._connection().execute(
            "INSERT INTO entries "
            "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry["sequence"],
                entry["event_id"],
                entry["actor"],
                entry["action"],
                entry["outcome"],
                entry["recorded_at"],
                entry["source_version"],
                json.dumps(entry.get("metadata", {})),
            ),
        )


def load_cohort_configuration(csv_path: Path) -> dict[str, str]:
    """Return {cohort: phase} for enabled rows of an upgrade-cohorts.csv file.

    Deterministic: `csv.DictReader` yields rows in file order, so the same
    file always produces the same dict. This duplicates the handful of
    lines in `auditlog.cohorts.load_cohort_phases` rather than importing it,
    because `auditlog.cohorts` already imports `resolve_v2_alias_catalog`
    from this module -- importing back would be circular. Loading this here
    only records configuration for a later phase to consult; it does not
    add a route, so it never changes what `ROUTE_ACTIONS` installs.
    """

    phases: dict[str, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["enabled"].strip().lower() == "true":
                phases[row["cohort"]] = row["phase"]
    return phases


def _event_payload(event) -> dict:
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


class AuditHTTPServer(ThreadingHTTPServer):
    """The daemon's server: carries the service, bearer secret, cohort
    configuration (recorded for later reference but never consulted for
    auth or handler selection), and the installed route/bearer tables --
    V1 routes plus every resolved, protected V2 alias -- the request
    handler dispatches against."""

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        service: AuditLogService,
        bearer_token: str,
        cohort_phases: dict[str, str],
        installed_routes: dict[tuple[str, str], str],
        installed_bearer: dict[tuple[str, str], bool],
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.service = service
        self.bearer_token = bearer_token
        self.cohort_phases = cohort_phases
        self.installed_routes = installed_routes
        self.installed_bearer = installed_bearer
        self.write_lock = threading.Lock()


class V1RequestHandler(BaseHTTPRequestHandler):
    """Dispatches every route in `self.server.installed_routes` -- V1 routes
    plus each protected V2 alias installed at server startup -- each
    bearer-protected per `self.server.installed_bearer`. Cohort phase
    (`self.server.cohort_phases`) is never consulted here."""

    protocol_version = "HTTP/1.0"
    server_version = "auditlogd/1"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass  # keep test output quiet; nothing here is a diagnostic signal

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, method: str, path: str) -> bool:
        if not self.server.installed_bearer.get((method, path), False):
            return True
        scheme, _, token = self.headers.get("Authorization", "").partition(" ")
        return scheme == "Bearer" and token == self.server.bearer_token

    def _dispatch(self) -> None:
        parsed = urlsplit(self.path)
        method = self.command

        # Route lookup and the auth decision happen before any body is read.
        auth_route = auth_path(parsed.path)
        if self.server.installed_routes.get((method, auth_route)) is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "no such route"})
            return
        if not self._authorized(method, auth_route):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "bearer token required"})
            return

        # Auth passed; the handler dispatches on the same path spelling.
        action = self.server.installed_routes[(method, dispatch_path(parsed.path))]
        service = self.server.service

        if action == "record":
            self._handle_record(service)
        elif action == "query":
            self._handle_query(service, parse_qs(parsed.query))
        elif action == "integrity":
            self._handle_integrity(service)

    def _handle_record(self, service: AuditLogService) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return
        try:
            with self.server.write_lock:
                event = service.record(
                    payload["actor"],
                    payload["action"],
                    payload["outcome"],
                    metadata=payload.get("metadata"),
                    recorded_at=payload.get("recorded_at"),
                )
        except KeyError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"missing field {exc}"})
            return
        self._send_json(HTTPStatus.CREATED, _event_payload(event))

    def _handle_query(self, service: AuditLogService, query: dict[str, list[str]]) -> None:
        actor = query.get("actor", [None])[0]
        action = query.get("action", [None])[0]
        events = service.query(actor=actor, action=action)
        self._send_json(HTTPStatus.OK, {"entries": [_event_payload(event) for event in events]})

    def _handle_integrity(self, service: AuditLogService) -> None:
        try:
            events = service.verify()
        except (SequenceError, IntegrityError) as exc:
            self._send_json(HTTPStatus.CONFLICT, {"verified": False, "error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, {"verified": True, "count": len(events)})

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802 - stdlib signature
        self._dispatch()


def build_server(
    store_path: Path,
    bearer_token: str,
    cohorts_csv: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
) -> AuditHTTPServer:
    """Build (but do not start) the audit HTTP daemon.

    Persistence is `SqliteEventStore` at `store_path`. If `cohorts_csv` is
    given, its cohort-to-phase configuration is loaded once, deterministically
    (`load_cohort_configuration`) and kept on the server for a later phase to
    consult; cohort phase is never used to decide auth or handler selection,
    so a cohort configured for "v2" reaches the same installed `/v2/*` alias
    every other caller does, not a route chosen per cohort.

    The V2 alias catalog (`auditlog.policy.build_v2_alias_catalog`) is
    resolved here, once, through `resolve_v2_alias_catalog` against
    `auditlog.policy.CANONICAL_V1_BEARER`, and installed alongside
    `ROUTE_ACTIONS`: every resolved alias dispatches to the same handler as
    its canonical V1 route and carries the same bearer requirement. V1
    routes, and the 404 for any route named in neither table, are
    unchanged.
    """

    service = AuditLogService(SqliteEventStore(store_path))
    cohort_phases = load_cohort_configuration(cohorts_csv) if cohorts_csv is not None else {}

    resolved_aliases = resolve_v2_alias_catalog(build_v2_alias_catalog(), CANONICAL_V1_BEARER)
    installed_routes = dict(ROUTE_ACTIONS)
    installed_bearer = dict(CANONICAL_V1_BEARER)
    for method, path, permission, requires_auth in resolved_aliases:
        installed_routes[(method, path)] = permission
        installed_bearer[(method, path)] = requires_auth

    return AuditHTTPServer(
        (host, port),
        V1RequestHandler,
        service,
        bearer_token,
        cohort_phases,
        installed_routes,
        installed_bearer,
    )
