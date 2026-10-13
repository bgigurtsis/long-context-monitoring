"""Loopback HTTP surface for the audit log service, plus the alias-resolution seam.

Gateway path normalization (:mod:`auditlog.paths`) only changes how a
request's path is *spelled* -- decoding, slash-collapsing, trailing-slash
trimming, all bounded to a fixed set of accepted spellings -- so that a
documented path and a harmless alternate spelling reach the same route. A
path outside that bounded set (a control character, or percent-encoding that
is malformed, decodes to a control character, or decodes to ``/`` or ``%``)
is refused with 400 before authorization is even checked, rather than
guessed at. Every request is normalized exactly once, and that single
canonical path is what both the authorization lookup and the dispatch match
use -- there is no second normalization pass that could disagree with the
first. None of this changes whether a route needs a bearer token. That
decision belongs entirely to :func:`resolve_v2_alias_catalog`, and only for
alias entries that don't already carry an explicit ``requires_auth``:

* An alias with an explicit ``True``/``False`` here passes through
  unchanged; resolution never overrides an explicit answer.
* An alias with no explicit answer (``None``) inherits its canonical V1
  route's requirement, and falls back to ``True`` when that route is
  unknown -- normalization can add a bearer requirement, or look one up,
  but it can never invent an unauthenticated route or downgrade one.

At server startup, the V2 alias catalog built by
:func:`auditlog.policy.build_v2_alias_catalog` is resolved through
:func:`resolve_v2_alias_catalog` against the real V1 bearer table and
installed alongside the V1 routes. A V2 alias is reachable at exactly the
same normalized path its catalog entry declares, dispatches to the same
handler as its canonical V1 route, and is gated by its own resolved
``requires_auth`` -- never by the V1 route's requirement recomputed at
request time.

Every request is also run through :func:`auditlog.gateway.parse_gateway_envelope`,
which strictly validates an optional ``X-Gateway-Envelope`` header. That
validation decides only whether the request is well-formed; it is never
consulted for authentication. Authentication is decided solely by comparing
the request's own ``Authorization`` header against the server's configured
bearer token.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from auditlog.gateway import GatewayEnvelopeError, parse_gateway_envelope
from auditlog.models import AuditEvent
from auditlog.paths import PathNormalizationError, auth_path
from auditlog.policy import build_v2_alias_catalog
from auditlog.service import ArchiveFormatError, AuditService, SequenceError
from auditlog.store import LogStore

# The only V1 routes this server has ever had, and the (fixed) bearer
# requirement each one actually enforces today. This is the "canonical
# route table" that V2 aliases with an inherited (``None``) bearer
# requirement resolve against.
_V1_ROUTES: dict[tuple[str, str], str] = {
    ("POST", "/v1/entries"): "record",
    ("GET", "/v1/entries"): "query",
    ("GET", "/v1/integrity"): "integrity",
}
_V1_BEARER_REQUIREMENTS: dict[tuple[str, str], bool] = dict.fromkeys(_V1_ROUTES, True)


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve inherited aliases through their canonical V1 route keys.

    ``requires_auth`` is only ever filled in when it is ``None`` (inherited);
    an entry that already states ``True`` or ``False`` is returned as-is. An
    inherited entry with no canonical route to inherit from defaults to
    ``True``, the fail-secure answer.
    """

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            canonical_path_for_route = path.replace("/v2/", "/v1/", 1)
            requires_auth = canonical_bearer.get((method, canonical_path_for_route), True)
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


class LoopbackHostError(ValueError):
    """``--host`` did not resolve to a loopback-only address."""


def ensure_loopback_host(host: str) -> str:
    """Return ``host`` unchanged if it is loopback-only; raise otherwise.

    Accepts the literal ``localhost`` and any address in a loopback range
    (``127.0.0.0/8`` for IPv4, ``::1`` for IPv6). Everything else -- a
    wildcard bind, a LAN address, a public address, an unparseable name --
    is rejected before a socket is ever opened.
    """

    if host == "localhost":
        return host
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise LoopbackHostError(f"{host!r} is not a loopback host") from exc
    if not address.is_loopback:
        raise LoopbackHostError(f"{host!r} is not a loopback host")
    return host


def _event_json(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "metadata": event.metadata,
    }


def make_handler(
    service: AuditService,
    bearer_token: str,
    v2_routes: tuple[tuple[str, str, str, bool], ...] = (),
) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to one ``service`` and one bearer token.

    ``v2_routes`` is a catalog already resolved by
    :func:`resolve_v2_alias_catalog` -- every ``requires_auth`` here is a
    concrete ``True``/``False``, never ``None``. Each entry is installed
    into the same route table as the V1 routes, keyed by its own
    ``(method, path)``, so a V2 alias dispatches to the same handler as its
    canonical V1 route but is gated by its own resolved requirement. A V1
    route is never overridden by a same-keyed V2 entry.

    Every request path goes through the same four gates in order: strict
    envelope parsing (400 on malformed input, regardless of auth), bounded
    path normalization (400 on a control character or ambiguous
    percent-encoding, also regardless of auth), route lookup (404 for
    anything not in the installed V1 + V2 table), then that route's own
    bearer check (401). The envelope is parsed and the path normalized
    before the route lookup only because both are structural and cheap --
    neither result is used to grant or deny the auth decision that follows.
    Path normalization runs exactly once per request; the resulting
    canonical path is the only path the route decision or the handler ever
    sees, so there is no second normalization pass that could disagree with
    the first, and no way for a route decision to be made against one
    spelling and the actual handler invoked against another.
    """

    route_table: dict[tuple[str, str], tuple[str, bool]] = {
        key: (permission, _V1_BEARER_REQUIREMENTS[key]) for key, permission in _V1_ROUTES.items()
    }
    for method, path, permission, requires_auth in v2_routes:
        route_table.setdefault((method, path), (permission, requires_auth))

    class AuditRequestHandler(BaseHTTPRequestHandler):
        server_version = "auditlog/0.1"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
            pass

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            expected = f"Bearer {bearer_token}"
            return hmac.compare_digest(header, expected)

        def _handle(self, method: str) -> None:
            try:
                parse_gateway_envelope(self.headers.get("X-Gateway-Envelope"))
            except GatewayEnvelopeError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            split = urlsplit(self.path)
            try:
                # One normalization pass; this same string drives both the
                # route lookup and the dispatch match below -- for a V1
                # route or an installed V2 alias alike.
                path = auth_path(split.path)
            except PathNormalizationError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            route = route_table.get((method, path))
            if route is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "no such route"})
                return
            permission, requires_auth = route

            if requires_auth and not self._authorized():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "bearer token required"})
                return

            try:
                if permission == "record":
                    self._record()
                elif permission == "query":
                    self._query(split)
                elif permission == "integrity":
                    self._integrity()
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "no such route"})
            except (ValueError, SequenceError, ArchiveFormatError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def _record(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSON body: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            for field in ("actor", "action", "outcome"):
                if field not in payload:
                    raise ValueError(f"missing required field {field!r}")

            recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            event = service.record(
                payload["actor"],
                payload["action"],
                payload["outcome"],
                recorded_at,
                payload.get("metadata"),
            )
            self._send_json(HTTPStatus.CREATED, _event_json(event))

        def _query(self, split) -> None:
            query = parse_qs(split.query)
            actor = query.get("actor", [None])[0]
            action = query.get("action", [None])[0]
            events = service.query(actor=actor, action=action)
            self._send_json(HTTPStatus.OK, {"entries": [_event_json(event) for event in events]})

        def _integrity(self) -> None:
            report = service.repair()
            self._send_json(
                HTTPStatus.OK,
                {
                    "verified": report.verified,
                    "tampered": list(report.tampered),
                    "migrated": report.migrated,
                    "index_rebuilt": report.index_rebuilt,
                },
            )

        def do_POST(self) -> None:
            self._handle("POST")

        def do_GET(self) -> None:
            self._handle("GET")

    return AuditRequestHandler


def build_server(store: LogStore, bearer_token: str, host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    """Construct (but do not run) the loopback V1+V2 HTTP server.

    Resolves the turn-3 V2 alias catalog
    (:func:`auditlog.policy.build_v2_alias_catalog`) against the real V1
    bearer table (``_V1_BEARER_REQUIREMENTS``) and installs the resolved
    aliases alongside the V1 routes, so every server this function builds
    has always had its V2 aliases reachable -- there is no separate step
    that turns them on later.

    Separate from :func:`serve` so tests can start it on an OS-assigned port
    (``port=0``) in a background thread without blocking the process the way
    ``serve`` deliberately does.
    """

    ensure_loopback_host(host)
    service = AuditService(store)
    v2_routes = resolve_v2_alias_catalog(build_v2_alias_catalog(), _V1_BEARER_REQUIREMENTS)
    handler_cls = make_handler(service, bearer_token, v2_routes)
    return HTTPServer((host, port), handler_cls)


def serve(store: LogStore, bearer_token: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the loopback V1 HTTP surface in the foreground until interrupted."""

    server = build_server(store, bearer_token, host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
