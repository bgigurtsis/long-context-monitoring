"""Loopback HTTP service: public recovery endpoints plus bearer-authenticated
account administration and notification retry.
"""
from __future__ import annotations

import datetime as _dt
import hmac
import json
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional, Tuple

from . import service, storage, worker
from .errors import AuthError, ServiceError, ValidationError
from .jsonutil import dumps

_ACCOUNT_EMAIL_RE = re.compile(r"^/admin/accounts/(?P<account_id>[^/]+)/email$")
_ACCOUNT_MFA_RE = re.compile(r"^/admin/accounts/(?P<account_id>[^/]+)/mfa$")
_ACCOUNT_RE = re.compile(r"^/admin/accounts/(?P<account_id>[^/]+)$")

# Serializes all durable-store access from request handler threads. This is a
# loopback administration/recovery service, not a high-throughput API, so a
# single global lock is simpler and safer than per-connection tuning.
_db_lock = threading.Lock()


def make_handler(database_path: str, bearer_token: str, mail_endpoint: str, worker_generation: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "accountsvc/0.1"

        def log_message(self, format, *args):  # noqa: A002 - stdlib signature
            pass

        def _send_json(self, status: int, payload: dict) -> None:
            body = dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ServiceError(f"invalid JSON body: {exc}") from exc
            if not isinstance(data, dict):
                raise ServiceError("JSON body must be an object")
            return data

        def _require_auth(self) -> None:
            header = self.headers.get("Authorization", "")
            expected = f"Bearer {bearer_token}"
            if not hmac.compare_digest(header, expected):
                raise AuthError("missing or invalid bearer token")

        def _run(self, fn: Callable[[], Tuple[int, dict]]) -> None:
            try:
                status, payload = fn()
                self._send_json(status, payload)
            except ServiceError as exc:
                self._send_json(exc.status_code, {"error": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self):  # noqa: N802 - stdlib handler name
            path = self.path.rstrip("/") or "/"

            if path == "/recovery/start":
                def op():
                    body = self._read_json()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.start_recovery(
                            conn, mail_endpoint, body.get("organization", ""), body.get("email", ""),
                            worker_generation,
                        )
                    return int(HTTPStatus.ACCEPTED), result
                return self._run(op)

            if path == "/recovery/complete":
                def op():
                    body = self._read_json()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.complete_recovery(conn, body.get("token", ""))
                    return int(HTTPStatus.OK), result
                return self._run(op)

            if path == "/recovery/notifications/retry":
                def op():
                    self._require_auth()
                    body = self._read_json()
                    if body:
                        raise ValidationError(
                            "this endpoint takes no selector -- it always sweeps every "
                            "eligible failed notice; POST an empty JSON object"
                        )
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.retry_notifications(conn, mail_endpoint, worker_generation)
                    return int(HTTPStatus.OK), result
                return self._run(op)

            if path == "/admin/accounts":
                def op():
                    self._require_auth()
                    body = self._read_json()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.create_account(
                            conn,
                            body.get("organization_id", ""),
                            body.get("account_id", ""),
                            body.get("email", ""),
                        )
                    return int(HTTPStatus.CREATED), result
                return self._run(op)

            match = _ACCOUNT_EMAIL_RE.match(path)
            if match:
                account_id = match.group("account_id")

                def op():
                    self._require_auth()
                    body = self._read_json()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.change_email(conn, account_id, body.get("email", ""))
                    return int(HTTPStatus.OK), result
                return self._run(op)

            match = _ACCOUNT_MFA_RE.match(path)
            if match:
                account_id = match.group("account_id")

                def op():
                    self._require_auth()
                    body = self._read_json()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.add_mfa_factor(conn, account_id, body.get("label", ""))
                    return int(HTTPStatus.CREATED), result
                return self._run(op)

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_GET(self):  # noqa: N802 - stdlib handler name
            path = self.path.rstrip("/") or "/"

            if path == "/admin/worker/status":
                def op():
                    self._require_auth()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = worker.get_worker_status(conn, worker_generation)
                    return int(HTTPStatus.OK), result
                return self._run(op)

            if path == "/admin/audit-events":
                def op():
                    self._require_auth()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.list_audit_events(conn)
                    return int(HTTPStatus.OK), result
                return self._run(op)

            match = _ACCOUNT_RE.match(path)
            if match:
                account_id = match.group("account_id")

                def op():
                    self._require_auth()
                    with _db_lock, storage.connect(database_path) as conn:
                        result = service.show_account(conn, account_id)
                    return int(HTTPStatus.OK), result
                return self._run(op)

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    return Handler


def serve(
    database_path: str,
    bearer_token: str,
    mail_endpoint: str,
    host: str = "127.0.0.1",
    port: int = 0,
    clock_now: Optional[_dt.datetime] = None,
    recovery_token_ttl: Optional[_dt.timedelta] = None,
) -> ThreadingHTTPServer:
    """Build and bind the loopback HTTP server. Caller drives serve_forever().

    Before accepting connections, this establishes the process's own worker
    generation, resolves any notification checkpoint left ``in_progress`` by
    an earlier generation -- i.e. unfinished work from a process that
    crashed between persisting a delivery attempt and recording the
    provider's acknowledgement of it -- and prunes any pending request whose
    token has already expired.

    ``clock_now`` and ``recovery_token_ttl`` fix this process's notion of
    "now" and the recovery token TTL respectively -- normally left unset (so
    the real system clock and default TTL apply), they let a test simulate a
    process booting at a specific, possibly far-future instant relative to
    requests created by an earlier process, so expiry can be exercised
    deterministically instead of waiting on real elapsed time.
    """
    service.set_clock(clock_now)
    service.set_recovery_token_ttl(recovery_token_ttl)
    with storage.connect(database_path) as conn:
        worker_generation = worker.start_generation(conn)
        worker.recover_unfinished_notifications(conn, worker_generation)
        service.prune_expired_requests(conn)
    handler = make_handler(database_path, bearer_token, mail_endpoint, worker_generation)
    return ThreadingHTTPServer((host, port), handler)
