"""Loopback HTTP surface: public recovery endpoints plus authenticated
notification retry and administration endpoints. Every response body is
stable (sorted-key) JSON.
"""
from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import db, jsonutil, security, service
from .errors import InvalidRequestError, ServiceError, UnauthorizedError

_ADMIN_ACCOUNT = re.compile(r"^/admin/accounts/(?P<account_id>[^/]+)$")
_ADMIN_ORG_ACCOUNTS = re.compile(r"^/admin/organizations/(?P<organization_id>[^/]+)/accounts$")
_ADMIN_LEASES = re.compile(r"^/admin/queue/leases$")
_ADMIN_LEASE_RELEASE = re.compile(r"^/admin/queue/leases/(?P<attempt_id>\d+)/release$")
_ADMIN_QUEUE_WORKERS = re.compile(r"^/admin/queue/workers$")

# The reclaim endpoint selects purely by recorded lease expiry; a caller
# cannot target it at a specific account or redirect where a notice goes.
_RECLAIM_REJECTED_FIELDS = ("account_id", "recipient", "recipient_email")


class RecoveryServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        db_path: str,
        bearer_token: str,
        mail_endpoint: str,
        token_ttl_seconds: float = security.TOKEN_TTL_SECONDS,
        clock_now: float | None = None,
    ):
        self.db_path = db_path
        self.bearer_token = bearer_token
        self.mail_endpoint = mail_endpoint
        self.token_ttl_seconds = token_ttl_seconds
        # A fixed epoch, when set, replaces the real wall clock for every
        # request this server handles -- durability and expiry are all
        # measured against SQLite-stored timestamps, so freezing this is
        # enough to make an entire process's behavior deterministic.
        self.clock_now = clock_now
        super().__init__(address, RecoveryRequestHandler)


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    server: RecoveryServer

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass  # keep loopback test runs quiet; failures still surface as HTTP errors

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise ServiceError("request body is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ServiceError("request body must be a JSON object")
        return parsed

    def _require_bearer(self) -> None:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            raise UnauthorizedError("missing bearer token")
        supplied = header[len(prefix) :]
        if not security.constant_time_eq(supplied, self.server.bearer_token):
            raise UnauthorizedError("invalid bearer token")

    def _write(self, status: int, payload: dict) -> None:
        body = jsonutil.dumpb(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, dispatch) -> None:
        conn = db.connect(self.server.db_path)
        try:
            status, payload = dispatch(conn)
            self._write(status, payload)
        except ServiceError as exc:
            self._write(exc.http_status, {"error": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover - defensive backstop
            self._write(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": str(exc)})
        finally:
            conn.close()

    def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]

        if path == "/recovery/start":
            def dispatch(conn):
                body = self._read_json_body()
                result = service.start_recovery(
                    conn,
                    body.get("organization"),
                    body.get("email"),
                    self.server.mail_endpoint,
                    now=self.server.clock_now,
                    ttl_seconds=self.server.token_ttl_seconds,
                )
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if path == "/recovery/complete":
            def dispatch(conn):
                body = self._read_json_body()
                result = service.complete_recovery(
                    conn, body.get("token"), body.get("mfa_code"), now=self.server.clock_now
                )
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if path == "/recovery/notifications/retry":
            def dispatch(conn):
                self._require_bearer()
                body = self._read_json_body()
                if body:
                    raise InvalidRequestError(
                        "retry does not accept a request body; POST an empty JSON object"
                    )
                result = service.retry_notifications(conn, self.server.mail_endpoint, now=self.server.clock_now)
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if path == "/recovery/notification-leases/reclaim":
            def dispatch(conn):
                self._require_bearer()
                body = self._read_json_body()
                rejected = sorted(field for field in _RECLAIM_REJECTED_FIELDS if field in body)
                if rejected:
                    raise InvalidRequestError(
                        f"reclaim does not accept caller-supplied field(s): {', '.join(rejected)}"
                    )
                result = service.reclaim_expired_notification_leases(
                    conn,
                    now=self.server.clock_now,
                    worker_id=body.get("worker_id"),
                    batch_size=int(body.get("batch_size", 25)),
                )
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if path == "/recovery/notification-leases/cleanup-stale-owners":
            def dispatch(conn):
                self._require_bearer()
                body = self._read_json_body()
                result = service.cleanup_stale_lease_owners(
                    conn,
                    now=self.server.clock_now,
                    batch_size=int(body.get("batch_size", 25)),
                )
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        match = _ADMIN_LEASE_RELEASE.match(path)
        if match:
            def dispatch(conn):
                self._require_bearer()
                result = service.admin_release_lease(conn, int(match.group("attempt_id")), now=self.server.clock_now)
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        self._write(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": f"no route for POST {path}"})

    def do_GET(self):  # noqa: N802 - required by BaseHTTPRequestHandler
        path = self.path.split("?", 1)[0]

        match = _ADMIN_ACCOUNT.match(path)
        if match:
            def dispatch(conn):
                self._require_bearer()
                result = service.show_account(conn, match.group("account_id"))
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        match = _ADMIN_ORG_ACCOUNTS.match(path)
        if match:
            def dispatch(conn):
                self._require_bearer()
                result = service.list_accounts(conn, match.group("organization_id"))
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if _ADMIN_LEASES.match(path):
            def dispatch(conn):
                self._require_bearer()
                result = service.admin_list_leases(conn, now=self.server.clock_now)
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        if _ADMIN_QUEUE_WORKERS.match(path):
            def dispatch(conn):
                self._require_bearer()
                result = service.worker_status(conn, now=self.server.clock_now)
                return HTTPStatus.OK, result

            return self._handle(dispatch)

        self._write(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": f"no route for GET {path}"})


def create_server(
    host: str,
    port: int,
    db_path: str,
    bearer_token: str,
    mail_endpoint: str,
    token_ttl_seconds: float = security.TOKEN_TTL_SECONDS,
    clock_now: float | None = None,
) -> RecoveryServer:
    return RecoveryServer((host, port), db_path, bearer_token, mail_endpoint, token_ttl_seconds, clock_now)
