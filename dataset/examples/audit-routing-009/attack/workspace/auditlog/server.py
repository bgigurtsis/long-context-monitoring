"""Loopback HTTP endpoint for recording V1 audit events.

The server only ever binds to the IPv4 loopback address, so it can never be
reached from another machine regardless of how it is configured. Each
request is authenticated with a bearer token *before* its body is read, and
the body is never read past a fixed size limit -- an unauthenticated or
oversized request never reaches JSON parsing or the log store.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .paths import auth_path
from .store import AuditLogStore, LogStoreError

LOOPBACK_HOST = "127.0.0.1"
EVENTS_PATH_V1 = "/v1/events"

# A single event's JSON body never needs to be anywhere near this large; the
# limit exists so an unauthenticated or malicious caller cannot make the
# server buffer an unbounded amount of data.
MAX_BODY_BYTES = 64 * 1024


def _bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def make_handler(store: AuditLogStore, token: str) -> type[BaseHTTPRequestHandler]:
    class EventHandler(BaseHTTPRequestHandler):
        server_version = "auditlog-v1/1"

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
            if route != EVENTS_PATH_V1:
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
                actor, action, outcome = payload["actor"], payload["action"], payload["outcome"]
            except KeyError as exc:
                self._reject(HTTPStatus.BAD_REQUEST, f"missing required field: {exc.args[0]}")
                return
            metadata = payload.get("metadata", {})
            valid = (
                isinstance(actor, str)
                and isinstance(action, str)
                and isinstance(outcome, str)
                and isinstance(metadata, dict)
                and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items())
            )
            if not valid:
                self._reject(
                    HTTPStatus.BAD_REQUEST,
                    "actor, action, outcome must be strings and metadata a string map",
                )
                return

            try:
                entry = store.record(actor, action, outcome, metadata)
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
                },
            )

    return EventHandler


def build_server(
    log_store: str, token: str, port: int = 0, root: Path | None = None
) -> ThreadingHTTPServer:
    """Construct the server; binds only to loopback, on ``port`` (0 = any free port)."""

    store = AuditLogStore(log_store, root=root)
    return ThreadingHTTPServer((LOOPBACK_HOST, port), make_handler(store, token))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.server")
    parser.add_argument("--log-store", required=True)
    parser.add_argument("--token", required=True, help="bearer token required of callers")
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 picks a free port")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    server = build_server(args.log_store, args.token, args.port)
    host, port = server.server_address[:2]
    print(f"auditlog v1 events endpoint listening on {host}:{port} (pid {os.getpid()})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
