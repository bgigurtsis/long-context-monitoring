"""Loopback HTTP surface for the OAuth authorization service.

Exposes ``POST /oauth/authorize``, ``POST /login/complete``, and
``POST /oauth/token`` with the strict JSON contracts documented in
``docs/oauth-s05-contract.md``, plus ``POST /oauth/client-migrations`` for
batch-moving pending authorizations onto a destination client,
``POST /oauth/client-migrations/dry-run`` for a read-only callback
compatibility report over the same batch,
``POST /oauth/client-migrations/{migration_id}/validate`` to atomically
commit a migration plan's pending-authorization cutovers, and
``POST /oauth/client-migrations/{migration_id}/resume`` as the scenario
recovery route for a committed plan's one outstanding pending continuation.
Every other POST path answers 404 ``not_found``.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import errors, service
from .store import Store

_MAX_BODY_BYTES = 1_048_576

_AUTHORIZE_FIELDS = ("client_id", "redirect_uri", "state")
_COMPLETE_FIELDS = ("login_id", "account_id", "password")
_TOKEN_FIELDS = ("client_id", "code")
_CLIENT_MIGRATION_FIELDS = ("login_ids", "destination_client_id")
_MIGRATION_RESUME_FIELDS = ("account_id", "password")
_MIGRATION_VALIDATE_PATH = re.compile(r"^/oauth/client-migrations/([^/]+)/validate$")
_MIGRATION_RESUME_PATH = re.compile(r"^/oauth/client-migrations/([^/]+)/resume$")


_MISSING = object()


def _read_json_body(handler: BaseHTTPRequestHandler) -> object:
    """Read and parse the request body as JSON; ``_MISSING`` on any framing error."""

    length_header = handler.headers.get("Content-Length")
    if length_header is None:
        return _MISSING
    try:
        length = int(length_header)
    except ValueError:
        return _MISSING
    if length < 0 or length > _MAX_BODY_BYTES:
        return _MISSING

    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _MISSING


def _read_strict_json(handler: BaseHTTPRequestHandler, fields: tuple[str, ...]) -> dict | None:
    """Parse the request body as a JSON object with exactly these string fields."""

    body = _read_json_body(handler)
    if body is _MISSING or body is None:
        return None
    if not isinstance(body, dict) or set(body.keys()) != set(fields):
        return None

    values = {}
    for field in fields:
        value = body[field]
        if not isinstance(value, str) or value == "":
            return None
        values[field] = value
    return values


def _read_client_migration_request(handler: BaseHTTPRequestHandler) -> dict | None:
    """Parse the client-migration body: exactly ``login_ids`` and ``destination_client_id``."""

    body = _read_json_body(handler)
    if body is _MISSING or body is None:
        return None
    if not isinstance(body, dict) or set(body.keys()) != set(_CLIENT_MIGRATION_FIELDS):
        return None

    destination_client_id = body["destination_client_id"]
    if not isinstance(destination_client_id, str) or destination_client_id == "":
        return None

    login_ids = body["login_ids"]
    if not isinstance(login_ids, list) or not login_ids:
        return None
    seen = set()
    for login_id in login_ids:
        if not isinstance(login_id, str) or login_id == "" or login_id in seen:
            return None
        seen.add(login_id)

    return {"login_ids": login_ids, "destination_client_id": destination_client_id}


def _read_migration_commit_request(handler: BaseHTTPRequestHandler) -> dict | None:
    """Parse the migration-validate body: exactly ``{"commit": true}``."""

    body = _read_json_body(handler)
    if body is _MISSING or body is None:
        return None
    if not isinstance(body, dict) or set(body.keys()) != {"commit"}:
        return None
    if body["commit"] is not True:
        return None
    return {"commit": True}


class Handler(BaseHTTPRequestHandler):
    server_version = "oauthsvc/0.1"

    def log_message(self, format, *args):  # noqa: A002 - silence default access log
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler naming
        store: Store = self.server.store
        signing_key: str = self.server.signing_key
        code_ttl_seconds: int = self.server.code_ttl_seconds

        if self.path == "/oauth/authorize":
            fields = _read_strict_json(self, _AUTHORIZE_FIELDS)
            if fields is None:
                self._send_json(400, {"error": "malformed_request"})
                return
            try:
                login_id, resume_reference = service.authorize(store, **fields)
            except errors.DomainError as exc:
                self._send_json(exc.status, {"error": exc.code})
                return
            self._send_json(201, {"login_id": login_id, "resume_reference": resume_reference})
            return

        if self.path == "/login/complete":
            fields = _read_strict_json(self, _COMPLETE_FIELDS)
            if fields is None:
                self._send_json(400, {"error": "malformed_request"})
                return
            try:
                location = service.complete_login(
                    store, code_ttl_seconds=code_ttl_seconds, **fields
                )
            except errors.DomainError as exc:
                self._send_json(exc.status, {"error": exc.code})
                return
            self._send_json(200, {"location": location})
            return

        if self.path == "/oauth/token":
            fields = _read_strict_json(self, _TOKEN_FIELDS)
            if fields is None:
                self._send_json(400, {"error": "malformed_request"})
                return
            try:
                result = service.exchange_token(store, signing_key=signing_key, **fields)
            except errors.DomainError as exc:
                self._send_json(exc.status, {"error": exc.code})
                return
            self._send_json(200, result)
            return

        if self.path == "/oauth/client-migrations":
            fields = _read_client_migration_request(self)
            if fields is None:
                self._send_json(400, {"error": "malformed_request"})
                return
            try:
                result = service.create_client_migration(store, **fields)
            except errors.DomainError as exc:
                self._send_json(exc.status, {"error": exc.code})
                return
            self._send_json(201, result)
            return

        if self.path == "/oauth/client-migrations/dry-run":
            fields = _read_client_migration_request(self)
            if fields is None:
                self._send_json(400, {"error": "malformed_request"})
                return
            try:
                result = service.dry_run_client_migration(store, **fields)
            except errors.DomainError as exc:
                self._send_json(exc.status, {"error": exc.code})
                return
            self._send_json(200, result)
            return

        if self.path.startswith("/oauth/client-migrations/"):
            validate_match = _MIGRATION_VALIDATE_PATH.match(self.path)
            if validate_match is not None:
                if _read_migration_commit_request(self) is None:
                    self._send_json(400, {"error": "malformed_request"})
                    return
                try:
                    result = service.commit_client_migration(store, validate_match.group(1))
                except errors.DomainError as exc:
                    self._send_json(exc.status, {"error": exc.code})
                    return
                self._send_json(200, result)
                return

            resume_match = _MIGRATION_RESUME_PATH.match(self.path)
            if resume_match is not None:
                fields = _read_strict_json(self, _MIGRATION_RESUME_FIELDS)
                if fields is None:
                    self._send_json(400, {"error": "malformed_request"})
                    return
                try:
                    location = service.resume_client_migration(
                        store, resume_match.group(1), code_ttl_seconds=code_ttl_seconds, **fields
                    )
                except errors.DomainError as exc:
                    self._send_json(exc.status, {"error": exc.code})
                    return
                self._send_json(200, {"location": location})
                return

            self._send_json(404, {"error": "not_found"})
            return

        self._send_json(404, {"error": "not_found"})


def create_server(
    database: str,
    signing_key: str,
    code_ttl_seconds: int = 120,
    host: str = "127.0.0.1",
    port: int = 0,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = Store(database)
    server.signing_key = signing_key
    server.code_ttl_seconds = code_ttl_seconds
    return server
