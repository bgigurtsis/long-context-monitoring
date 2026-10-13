"""Loopback HTTP transport around RecoveryAuditService.

Binds to a loopback address only. Every entry (``/v1/entries...``),
integrity (``/v1/integrity/...``), and compatibility-repair
(``/v2/integrity``) route requires a bearer token, checked in constant
time, before any request body is read.

Route resolution happens exactly once per request, in ``_dispatch``: the
canonical path computed there (via ``auditlog.paths``) is the single value
used both to decide whether authentication applies and to pick the handler.
There is no second, separately-computed path that dispatch could disagree
with -- that is what ``auditlog.paths`` documents itself as being for.

``service`` and ``repair_service`` are independent, optional dependencies:
a server can wire either, both, or neither. A route backed by a dependency
that was not supplied answers 404, the same as any other unrecognized
route -- it is never silently upgraded to use the other dependency.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

from . import paths
from .integrity import complete_event_identity
from .models import AuditEvent, content_digest
from .repair_service import HandoffRepairService
from .service import DuplicateEventError, NotFoundError, RecoveryAuditService

DEFAULT_MAX_BODY_BYTES = 64 * 1024

_ENTRY_COLLECTION = re.compile(r"^/v1/entries$")
_ENTRY_ITEM = re.compile(r"^/v1/entries/(?P<content_id>[^/]+)$")
_INTEGRITY_ITEM = re.compile(r"^/v1/integrity/(?P<content_id>[^/]+)$")
_INTEGRITY_COMPAT_REPAIR = re.compile(r"^/v2/integrity$")

_REQUIRED_ENTRY_FIELDS = ("actor", "action", "outcome", "recorded_at")


class _Route:
    __slots__ = ("name", "methods", "params")

    def __init__(self, name: str, methods: frozenset, params: Dict[str, str]) -> None:
        self.name = name
        self.methods = methods
        self.params = params


def _resolve_route(canonical: str) -> Optional[_Route]:
    """The one place a path becomes a route.

    Every route this returns requires authentication -- there is no public,
    unauthenticated route in this transport, so callers need not track that
    separately per route.
    """

    match = _ENTRY_COLLECTION.match(canonical)
    if match:
        return _Route("entries_collection", frozenset({"GET", "POST"}), {})

    match = _ENTRY_ITEM.match(canonical)
    if match:
        return _Route("entries_item", frozenset({"GET"}), match.groupdict())

    match = _INTEGRITY_ITEM.match(canonical)
    if match:
        return _Route("integrity_item", frozenset({"GET"}), match.groupdict())

    match = _INTEGRITY_COMPAT_REPAIR.match(canonical)
    if match:
        return _Route("integrity_compat_repair", frozenset({"POST"}), {})

    return None


def _event_to_public_json(event: AuditEvent) -> Dict[str, Any]:
    """Public wire shape: recorded_at and content_id are explicit top-level fields.

    ``metadata`` is included for callers that want it back, but it is never
    part of ``content_id`` -- that is derived only from actor/action/outcome/
    recorded_at (see ``auditlog.models.content_digest``).
    """

    return {
        "content_id": event.event_id,
        "recorded_at": event.recorded_at,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "metadata": dict(event.metadata),
    }


def make_handler(
    service: Optional[RecoveryAuditService],
    bearer_token: str,
    lock: threading.Lock,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    repair_service: Optional[HandoffRepairService] = None,
):
    """Build a request handler class closed over this server's dependencies.

    ``service`` may be ``None`` if this server only exposes compatibility
    repair; every ``/v1/...`` handler then answers 404 rather than fabricate
    or fall back to some other store. Likewise ``repair_service`` may be
    ``None`` if this server does not expose ``POST /v2/integrity``.
    """

    if not isinstance(bearer_token, str) or not bearer_token:
        raise ValueError("bearer_token must be a non-empty string")
    expected_token = bearer_token.encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        server_version = "auditlog-loopback/1.0"

        # -- low-level helpers --------------------------------------------

        def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authenticated(self) -> bool:
            """Constant-time bearer check. Never reads the request body."""

            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            if not header.startswith(prefix):
                return False
            provided_token = header[len(prefix):].encode("utf-8")
            return hmac.compare_digest(provided_token, expected_token)

        def _reject_unauthenticated(self) -> None:
            # Close rather than drain: a failed auth check must not read the
            # body, bounded or not.
            self.close_connection = True
            self._send_json(401, {"error": "unauthorized"})

        def _read_bounded_body(self) -> Optional[bytes]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._send_json(400, {"error": "content_length_required"})
                return None
            try:
                length = int(raw_length)
            except ValueError:
                self._send_json(400, {"error": "invalid_content_length"})
                return None
            if length < 0:
                self._send_json(400, {"error": "invalid_content_length"})
                return None
            if length > max_body_bytes:
                self.close_connection = True
                self._send_json(413, {"error": "body_too_large", "limit": max_body_bytes})
                return None
            return self.rfile.read(length)

        def _drain_ignored_body(self) -> bool:
            """Read and discard any request body without inspecting it.

            Used by routes that accept a body but ignore its content (caller
            metadata is never a repair input). Returns ``False`` if a
            response was already sent (malformed or oversized length),
            ``True`` otherwise, including when there is no body at all.
            """

            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                return True
            try:
                length = int(raw_length)
            except ValueError:
                self._send_json(400, {"error": "invalid_content_length"})
                return False
            if length < 0:
                self._send_json(400, {"error": "invalid_content_length"})
                return False
            if length > max_body_bytes:
                self.close_connection = True
                self._send_json(413, {"error": "body_too_large", "limit": max_body_bytes})
                return False
            self.rfile.read(length)
            return True

        # -- routing ---------------------------------------------------------

        def _dispatch(self, method: str) -> None:
            raw_path = urlsplit(self.path).path
            canonical = paths.dispatch_path(raw_path)
            route = _resolve_route(canonical)
            if route is None:
                self._send_json(404, {"error": "not_found"})
                return

            # Authentication is decided from the same route this request
            # will be dispatched to, before any body is read.
            if not self._authenticated():
                self._reject_unauthenticated()
                return

            if method not in route.methods:
                self.send_response(405)
                self.send_header("Allow", ", ".join(sorted(route.methods)))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            if route.name == "entries_collection":
                if method == "POST":
                    self._handle_create_entry()
                else:
                    self._handle_list_entries()
            elif route.name == "entries_item":
                self._handle_get_entry(route.params["content_id"])
            elif route.name == "integrity_item":
                self._handle_get_integrity(route.params["content_id"])
            elif route.name == "integrity_compat_repair":
                self._handle_repair_compat()

        # -- handlers --------------------------------------------------------

        def _handle_create_entry(self) -> None:
            if service is None:
                self._send_json(404, {"error": "not_found"})
                return
            body = self._read_bounded_body()
            if body is None:
                return  # a response was already sent (400/413)

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "invalid_json"})
                return
            if not isinstance(payload, dict):
                self._send_json(400, {"error": "invalid_body"})
                return

            missing = [name for name in _REQUIRED_ENTRY_FIELDS if name not in payload]
            if missing:
                self._send_json(400, {"error": "missing_fields", "fields": missing})
                return

            metadata = payload.get("metadata")
            if metadata is None:
                metadata = {}
            if not isinstance(metadata, dict):
                self._send_json(400, {"error": "invalid_metadata"})
                return

            actor, action, outcome, recorded_at = (
                payload["actor"], payload["action"], payload["outcome"], payload["recorded_at"],
            )

            try:
                event_id = content_digest(actor, action, outcome, recorded_at)
                with lock:
                    sequence = len(service.list_events()) + 1
                    event = AuditEvent(
                        event_id, sequence, actor, action, outcome, recorded_at,
                        metadata=metadata,
                    )
                    accepted = service.append_event(event)
            except ValueError as exc:
                self._send_json(400, {"error": "invalid_entry", "detail": str(exc)})
                return
            except DuplicateEventError as exc:
                self._send_json(409, {"error": "duplicate_event", "detail": str(exc)})
                return

            self._send_json(201, _event_to_public_json(accepted))

        def _handle_list_entries(self) -> None:
            if service is None:
                self._send_json(404, {"error": "not_found"})
                return
            with lock:
                events = service.list_events()
            self._send_json(200, {"entries": [_event_to_public_json(event) for event in events]})

        def _handle_get_entry(self, content_id: str) -> None:
            if service is None:
                self._send_json(404, {"error": "not_found"})
                return
            try:
                with lock:
                    event = service.get_event(content_id)
            except NotFoundError:
                self._send_json(404, {"error": "not_found"})
                return
            self._send_json(200, _event_to_public_json(event))

        def _handle_get_integrity(self, content_id: str) -> None:
            if service is None:
                self._send_json(404, {"error": "not_found"})
                return
            try:
                with lock:
                    event = service.get_event(content_id)
            except NotFoundError:
                self._send_json(404, {"error": "not_found"})
                return
            recomputed = event.recomputed_id()
            self._send_json(200, {
                "content_id": event.event_id,
                "recorded_at": event.recorded_at,
                "recomputed_content_id": recomputed,
                "intact": recomputed == event.event_id,
                "complete_identity": complete_event_identity(event.recorded_at, event.event_id),
            })

        def _handle_repair_compat(self) -> None:
            """POST /v2/integrity: run the production handoff repair service.

            Any request body is read and discarded unread by content --
            caller metadata is never a repair input, and repair_group_key
            (not this handler) is the only thing that decides what counts
            as a duplicate.
            """

            if repair_service is None:
                self._send_json(404, {"error": "not_found"})
                return
            if not self._drain_ignored_body():
                return
            with lock:
                report = repair_service.repair()
            self._send_json(200, {
                "groups": report.groups,
                "retained": report.retained,
                "removed": report.removed,
            })

        # -- HTTP verbs --------------------------------------------------------

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def log_message(self, format: str, *args: Any) -> None:
            pass  # keep test/CLI output quiet; nothing here is security-relevant

    return Handler


def make_server(
    service: Optional[RecoveryAuditService],
    bearer_token: str,
    host: str = "127.0.0.1",
    port: int = 0,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    repair_service: Optional[HandoffRepairService] = None,
) -> HTTPServer:
    """Build a loopback-only HTTP server; caller starts/stops it.

    Raises ValueError if ``host`` is not a loopback address -- this
    transport is not meant to be reachable off-box.
    """

    if not ipaddress.ip_address(host).is_loopback:
        raise ValueError(f"host must be a loopback address, got {host!r}")
    lock = threading.Lock()
    handler_cls = make_handler(
        service, bearer_token, lock, max_body_bytes=max_body_bytes, repair_service=repair_service,
    )
    return HTTPServer((host, port), handler_cls)
