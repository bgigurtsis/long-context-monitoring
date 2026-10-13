"""Loopback HTTP transport around the storage-independent audit service.

Binds to 127.0.0.1 only, per the project's local-only requirement. Every
entry and integrity route requires a constant-time bearer check before any
request body is read or parsed: an unauthenticated request is refused, and
its connection is closed, without ever touching the body.

The route table drives both the authentication decision and the dispatch
decision from one canonicalized path (``auditlog.paths.auth_path`` /
``dispatch_path`` -- ``dispatch_path`` is defined as returning
``auth_path``'s own result), so a documented path and a harmless alternate
spelling can never reach different decisions for "does this need auth" than
for "which handler serves it."

The server never accepts a caller-supplied receipt: POST /v1/entries only
reads ``actor``, ``action``, ``outcome``, ``payload``, ``recorded_at``, and
optional ``metadata`` from the request body -- there is no field a client
can use to supply or select a receipt. For every accepted entry, the
handler builds the immutable ``Event`` from exactly those accepted fields,
then calls ``identity_bound_http_receipt`` exactly once using that event's
own stored actor/action/outcome/payload/recorded_at/content_id -- never a
header, a metadata value, a path component, or a window label (HTTP
ingestion never has a window at all). The returned receipt is handed to the
service as private, server-owned evidence. Every public response -- the
creation response and query results alike -- exposes only actor, action,
outcome, recorded_at, content_id, sequence, and metadata; the receipt is
never serialized back to a caller.

POST /v2/integrity runs compatibility repair (see
``auditlog.compatibility_repair``): it reads and discards any request body
-- a caller supplies nothing that affects the outcome -- then delegates
entirely to the production non-mutating planner and the atomic removal
service, under a fresh, per-request lease owner so two concurrent repair
attempts serialize rather than racing; a repair already in flight is
reported with 409 Conflict, not a dropped connection. The response reports
which rows were kept and removed per actionable group, and which
verified-lineage groups were left untouched; it never includes a receipt or
a raw lineage value.
"""

from __future__ import annotations

import hmac
import json
import threading
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Mapping
from urllib.parse import parse_qs, urlsplit

from auditlog.compatibility_repair import CompatibilityRepairResult, execute_compatibility_repair
from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import CopyObservation, Event
from auditlog.overlap_planning import LeaseNotHeldError
from auditlog.paths import auth_path, dispatch_path
from auditlog.service import AuditService

_REPAIR_LEASE_TTL_SECONDS = 30.0

MAX_BODY_BYTES = 64 * 1024

_REQUIRED_ENTRY_FIELDS = ("actor", "action", "outcome", "payload", "recorded_at")
_OPTIONAL_ENTRY_FIELDS = ("metadata",)
_ALLOWED_ENTRY_FIELDS = frozenset(_REQUIRED_ENTRY_FIELDS + _OPTIONAL_ENTRY_FIELDS)


def _public_copy(row: CopyObservation) -> dict[str, Any]:
    """Fields safe to hand back to any caller. Never the private receipt."""

    return {
        "sequence": row.sequence,
        "actor": row.event.actor,
        "action": row.event.action,
        "outcome": row.event.outcome,
        "recorded_at": row.event.recorded_at,
        "content_id": row.event.content_id,
        "metadata": dict(row.metadata),
    }


def _public_repair_result(result: CompatibilityRepairResult) -> dict[str, Any]:
    """Fields safe to hand back for a repair outcome. Never a receipt or a raw lineage value."""

    return {
        "removed": [
            {
                "basis": group.basis,
                "retained_sequence": group.retained_sequence,
                "removed_sequences": list(group.removed_sequences),
                "window_labels": list(group.window_labels),
            }
            for group in result.removed_groups
        ],
        "retained_lineage_groups": [
            {
                "member_sequences": list(group.member_sequences),
                "window_labels": list(group.window_labels),
            }
            for group in result.retained_lineage_groups
        ],
    }


@dataclass(frozen=True)
class _Route:
    handler_name: str
    requires_auth: bool
    category: str  # "entry" | "integrity"


# Keyed by (method, canonical path). Both the auth decision and the dispatch
# decision come from this one table for one canonicalized path -- there is
# no second, independently-computed lookup that could disagree with it.
_ROUTES: dict[tuple[str, str], _Route] = {
    ("POST", "/v1/entries"): _Route("create_entry", True, "entry"),
    ("GET", "/v1/entries"): _Route("query_entries", True, "entry"),
    ("GET", "/v1/integrity/duplicate-cohorts"): _Route("duplicate_cohorts", True, "integrity"),
    ("POST", "/v2/integrity"): _Route("compatibility_repair", True, "integrity"),
}


class AuditRequestHandler(BaseHTTPRequestHandler):
    service: AuditService
    bearer_token: str

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    # -- routing ---------------------------------------------------------
    def _resolve(self) -> tuple[_Route | None, dict[str, list[str]]]:
        split = urlsplit(self.path)
        decision = auth_path(split.path)
        route = _ROUTES.get((self.command, decision))
        # dispatch_path never makes an independent choice: it returns
        # auth_path's own result, so this is the same route decision, not a
        # second one.
        assert dispatch_path(split.path) == decision
        return route, parse_qs(split.query)

    def _authenticated(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        presented = header[len(prefix):]
        return hmac.compare_digest(presented, self.bearer_token)

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _refuse(self, status: HTTPStatus, message: str) -> None:
        # An error response may be issued before a pending request body has
        # been read (unauthenticated or unroutable requests never read the
        # body at all); closing the connection avoids leaving unread bytes
        # on a keep-alive socket that would corrupt the next request.
        self.close_connection = True
        self._send_json(status, {"error": message})

    def _read_bounded_body(self) -> bytes | None:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            self._refuse(HTTPStatus.LENGTH_REQUIRED, "Content-Length is required")
            return None
        try:
            length = int(raw_length)
        except ValueError:
            self._refuse(HTTPStatus.BAD_REQUEST, "Content-Length must be an integer")
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self._refuse(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body exceeds the size bound")
            return None
        return self.rfile.read(length)

    def _dispatch(self) -> None:
        route, query = self._resolve()
        if route is None:
            self._refuse(HTTPStatus.NOT_FOUND, "no such route")
            return
        if route.requires_auth and not self._authenticated():
            self._refuse(HTTPStatus.UNAUTHORIZED, "authentication required")
            return
        getattr(self, route.handler_name)(query)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    # -- handlers ----------------------------------------------------------
    def create_entry(self, query: Mapping[str, list[str]]) -> None:
        raw = self._read_bounded_body()
        if raw is None:
            return
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._refuse(HTTPStatus.BAD_REQUEST, "invalid JSON body")
            return
        if not isinstance(body, dict):
            self._refuse(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
            return

        extra = sorted(set(body) - _ALLOWED_ENTRY_FIELDS)
        if extra:
            # Rejecting anything outside the known field set is what makes
            # it structurally impossible for a caller to smuggle a receipt,
            # a window label, or any other value into the accepted fields.
            self._refuse(HTTPStatus.BAD_REQUEST, f"unsupported fields: {extra}")
            return
        missing = [field for field in _REQUIRED_ENTRY_FIELDS if field not in body]
        if missing:
            self._refuse(HTTPStatus.BAD_REQUEST, f"missing required fields: {missing}")
            return

        actor, action, outcome, recorded_at = (
            body["actor"], body["action"], body["outcome"], body["recorded_at"],
        )
        payload = body["payload"]
        metadata = body.get("metadata", {})
        if not all(isinstance(value, str) for value in (actor, action, outcome, recorded_at)):
            self._refuse(HTTPStatus.BAD_REQUEST, "actor, action, outcome, and recorded_at must be strings")
            return
        if not isinstance(payload, dict):
            self._refuse(HTTPStatus.BAD_REQUEST, "payload must be a JSON object")
            return
        if not isinstance(metadata, dict):
            self._refuse(HTTPStatus.BAD_REQUEST, "metadata must be a JSON object")
            return

        event = Event.record(actor, action, outcome, payload, recorded_at)
        receipt = identity_bound_http_receipt(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at, event.content_id,
        )
        row = self.service.append(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at,
            source="http", stored_receipt=receipt, metadata=metadata,
        )
        self._send_json(HTTPStatus.CREATED, _public_copy(row))

    def query_entries(self, query: Mapping[str, list[str]]) -> None:
        def one(name: str) -> str | None:
            values = query.get(name)
            return values[0] if values else None

        rows = self.service.query(
            actor=one("actor"), action=one("action"), outcome=one("outcome"), content_id=one("content_id"),
        )
        self._send_json(HTTPStatus.OK, [_public_copy(row) for row in rows])

    def duplicate_cohorts(self, query: Mapping[str, list[str]]) -> None:
        cohorts = self.service.duplicate_cohorts()
        self._send_json(HTTPStatus.OK, [[_public_copy(row) for row in cohort] for cohort in cohorts])

    def compatibility_repair(self, query: Mapping[str, list[str]]) -> None:
        raw = self._read_bounded_body()
        if raw is None:
            return
        # The body, if any, is read only to keep the connection well-formed
        # and is then fully ignored: no caller-supplied field can select a
        # receipt, lineage, group, repair key, window, or retention choice.
        # Every decision comes from the reader's own server-verified result.
        owner = f"http-v2-integrity:{uuid.uuid4()}"
        try:
            result = execute_compatibility_repair(self.service, owner=owner, ttl_seconds=_REPAIR_LEASE_TTL_SECONDS)
        except LeaseNotHeldError:
            self._send_json(HTTPStatus.CONFLICT, {"error": "a compatibility repair is already in progress"})
            return
        self._send_json(HTTPStatus.OK, _public_repair_result(result))


class LoopbackAuditServer:
    """A stdlib-only, loopback-bound HTTP front end for an ``AuditService``."""

    def __init__(self, service: AuditService, bearer_token: str, *, host: str = "127.0.0.1", port: int = 0) -> None:
        handler = type(
            "_BoundAuditRequestHandler",
            (AuditRequestHandler,),
            {"service": service, "bearer_token": bearer_token},
        )
        self._httpd = HTTPServer((host, port), handler)
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
