"""Loopback HTTP endpoint for bearer-authenticated partner event ingress.

A partner event names the partner it came from; the partner's mapping (kept
in a :class:`~partner_mapping.PartnerMappingStore`) says which tenant-scoped
audit store the event belongs in. As with the V1 events endpoint, the bearer
token is checked and the route matched before the request body is read, and
a body over the size limit is rejected without being parsed.

The V2 entries endpoint resolves that destination through
:func:`~partner_mapping.load_effective_tenant_destination`, the offline
helper that loads a partner's mapping record straight from storage and sorts
its history before resolving, rather than through
:meth:`~partner_mapping.PartnerMappingStore.resolve_destination` directly.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from partner_mapping import PartnerMappingStore, load_effective_tenant_destination

from .paths import auth_path
from .server import LOOPBACK_HOST, MAX_BODY_BYTES
from .store import AuditLogStore, LogStoreError

PARTNER_EVENTS_PATH_V1 = "/v1/partner-events"
PARTNER_ENTRIES_PATH_V2 = "/v2/entries"


def _bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _tenant_store_path(destination: str) -> str:
    """The log-store path for a tenant's own audit trail."""

    return f"tenants/{destination}.db"


def make_partner_handler(
    mapping_store: PartnerMappingStore, token: str, root: Path | None
) -> type[BaseHTTPRequestHandler]:
    class PartnerEventHandler(BaseHTTPRequestHandler):
        server_version = "auditlog-partner-ingress/1"

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
            pass  # quiet by default; this is a local service, not a web server

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _reject(self, status: HTTPStatus, message: str) -> None:
            # Don't try to drain a body we never read (or refused to read in
            # full); just close the connection after the error response.
            self.close_connection = True
            self._send_json(status, {"error": message})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
            route = auth_path(self.path)
            if route == PARTNER_EVENTS_PATH_V1:
                resolve_destination = mapping_store.resolve_destination
            elif route == PARTNER_ENTRIES_PATH_V2:

                def resolve_destination(partner_id: str) -> str | None:
                    return load_effective_tenant_destination(mapping_store, partner_id)

            else:
                self._reject(HTTPStatus.NOT_FOUND, "no such route")
                return

            # Authenticate before doing any work on the request body.
            supplied = _bearer_token(self.headers.get("Authorization"))
            if supplied is None or not hmac.compare_digest(supplied, token):
                self._reject(HTTPStatus.UNAUTHORIZED, "missing or invalid bearer token")
                return

            raw_length = self.headers.get("Content-Length")
            if raw_length is None or not raw_length.isdigit():
                self._reject(HTTPStatus.LENGTH_REQUIRED, "Content-Length header is required")
                return
            length = int(raw_length)
            if length > MAX_BODY_BYTES:
                self._reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body is too large")
                return

            raw_body = self.rfile.read(length)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._reject(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
                return
            if not isinstance(payload, dict):
                self._reject(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
                return

            try:
                partner_id = payload["partner_id"]
                actor, action, outcome = payload["actor"], payload["action"], payload["outcome"]
            except KeyError as exc:
                self._reject(HTTPStatus.BAD_REQUEST, f"missing required field: {exc.args[0]}")
                return
            metadata = payload.get("metadata", {})
            valid = (
                isinstance(partner_id, str)
                and isinstance(actor, str)
                and isinstance(action, str)
                and isinstance(outcome, str)
                and isinstance(metadata, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items())
            )
            if not valid:
                self._reject(
                    HTTPStatus.BAD_REQUEST,
                    "partner_id, actor, action, outcome must be strings and metadata a string map",
                )
                return

            # The ordinary mapping path: resolve the partner's effective
            # tenant destination through whichever resolver this route uses,
            # so ingress and any other reader of a mapping agree on which
            # destination is current.
            destination = resolve_destination(partner_id)
            if destination is None:
                self._reject(HTTPStatus.NOT_FOUND, f"no mapping for partner {partner_id!r}")
                return

            try:
                tenant_store = AuditLogStore(_tenant_store_path(destination), root=root)
                entry = tenant_store.record(actor, action, outcome, metadata)
            except LogStoreError as exc:
                self._reject(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
                return

            self._send_json(
                HTTPStatus.CREATED,
                {
                    "event_id": entry.event_id,
                    "sequence": entry.sequence,
                    "actor": entry.actor,
                    "action": entry.action,
                    "outcome": entry.outcome,
                    "recorded_at": entry.recorded_at,
                    "metadata": entry.metadata,
                    "partner_id": partner_id,
                    "tenant_destination": destination,
                },
            )

    return PartnerEventHandler


def build_partner_ingress_server(
    mapping_store_path: str, token: str, port: int = 0, root: Path | None = None
) -> ThreadingHTTPServer:
    """Construct the server; binds only to loopback, on ``port`` (0 = any free port)."""

    mapping_store = PartnerMappingStore(mapping_store_path, root=root)
    return ThreadingHTTPServer(
        (LOOPBACK_HOST, port), make_partner_handler(mapping_store, token, root)
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.partner_ingress")
    parser.add_argument("--mapping-store", required=True)
    parser.add_argument("--token", required=True, help="bearer token required of callers")
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 picks a free port")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    server = build_partner_ingress_server(args.mapping_store, args.token, args.port)
    host, port = server.server_address[:2]
    print(f"auditlog v1 partner ingress endpoint listening on {host}:{port} (pid {os.getpid()})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
