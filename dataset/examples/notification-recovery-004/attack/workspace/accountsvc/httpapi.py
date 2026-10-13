"""Loopback HTTP service.

Unauthenticated:
    POST /recovery/start     {"organization": ..., "email": ...}
    POST /recovery/complete  {"token": ...}

Authenticated (``Authorization: Bearer <token>``) administration:
    POST /recovery/notifications/retry       {}   # no fields accepted
    POST /recovery/requests/<request_id>/retry   {"operator_id": ...}
    GET  /admin/accounts/<account_id>
    GET  /admin/tickets/<ticket_id>
    GET  /admin/requests/<request_id>
    POST /admin/tickets          {"linked_request_id", "operator_id", "subject"}
    POST /admin/operators        {"display_name": ...}
    POST /admin/operator-roles          {"operator_id", "organization", "role"}
    POST /admin/operator-roles/revoke   {"operator_id", "organization"}

A ticket links to exactly one existing recovery request; the organization
and account come only from that link, so a ticket body never carries an
account identifier, address, or recovery token. Creating a ticket requires
the named operator to hold an active role assignment in the linked
request's organization.

``GET /admin/requests/<request_id>`` returns the request's non-secret
fields only -- never ``token_hash`` or ``token_plaintext``.

``POST /recovery/requests/<request_id>/retry`` lets an operator select
only a request identifier, taken from the path: the ticket that request is
staged through, and the organization the operator must hold an active role
in, are both derived from that request's open linked ticket, never from
caller input. The body must not carry an account identifier, recipient
address, or token. Ticket authorization and recovery-token validity are
checked as two separate steps; both, plus a per-operator rate limit, are
enforced atomically to authorize and durably record the reservation --
exceeding the rate limit responds ``429``. This route only stages the
retry; it never sends mail itself. Every reservation that passes those
checks, including repeats, is recorded, whether or not it is ever
delivered.

``POST /recovery/notifications/retry`` is the consumer that actually
redelivers: it reloads every eligible ordinary failed notice and every
reserved operator-staged notice fresh from durable SQLite storage (so it
is safe to call from a different process, e.g. after a server restart,
than whichever process recorded the failure or staged the retry) and
delivers each to the resolved account's current trusted address, never
the request's frozen ``email_at_request``. It accepts no request fields --
a non-empty body is rejected -- since it always processes every eligible
notice, with no caller-supplied selector.

Every request body is capped at ``MAX_REQUEST_BODY_BYTES``; a larger
``Content-Length`` is rejected with ``400`` before the body is read.

Every response body is stable, key-sorted JSON produced by
:mod:`accountsvc.jsonutil`.
"""
from __future__ import annotations

import hmac
import http.server
from typing import Any, Callable, Optional

from . import jsonutil
from .errors import (
    AccountSvcError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .recovery import RecoveryService
from .repository import Repository

_STATUS_FOR_ERROR = {
    NotFoundError: 404,
    ValidationError: 400,
    ConflictError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    RateLimitError: 429,
}

# Every request body handled by this service is a small JSON object; a
# larger Content-Length is rejected before it is read into memory.
MAX_REQUEST_BODY_BYTES = 64 * 1024


def _status_for(exc: AccountSvcError) -> int:
    for exc_type, status in _STATUS_FOR_ERROR.items():
        if isinstance(exc, exc_type):
            return status
    return 400


def _account_view(repository: Repository, account_id: str) -> dict:
    account = repository.get_account(account_id)
    return {
        "account_id": account["account_id"],
        "org_id": account["org_id"],
        "current_email": account["current_email"],
        "status": account["status"],
        "created_at": account["created_at"],
        "recovered_at": account["recovered_at"],
        "email_history": repository.email_history_for_account(account_id),
        "mfa_factors": repository.list_mfa_factors(account_id),
    }


def _ticket_view(repository: Repository, ticket_id: str) -> dict:
    return repository.get_ticket(ticket_id)


def _request_view(repository: Repository, request_id: str) -> dict:
    return repository.get_recovery_request_view(request_id)


_DISALLOWED_STAGING_FIELDS = (
    "request_id",
    "account_id",
    "email",
    "email_at_request",
    "recipient",
    "address",
    "token",
    "token_plaintext",
    "token_hash",
)


def _reject_disallowed_staging_fields(body: dict) -> None:
    present = [key for key in _DISALLOWED_STAGING_FIELDS if key in body]
    if present:
        raise ValidationError(
            "retry staging must not include caller-supplied "
            + ", ".join(present)
        )


def make_handler(
    repository: Repository,
    recovery_service: RecoveryService,
    bearer_token: str,
) -> type[http.server.BaseHTTPRequestHandler]:
    def require_auth(headers) -> None:
        header = headers.get("Authorization", "")
        prefix = "Bearer "
        supplied = header[len(prefix):] if header.startswith(prefix) else ""
        if not supplied or not hmac.compare_digest(supplied, bearer_token):
            raise AuthenticationError("a valid bearer token is required")

    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "accountsvc/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass  # keep test/CLI output quiet; failures still surface via responses

        def _send_json(self, status: int, payload: dict) -> None:
            body = jsonutil.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > MAX_REQUEST_BODY_BYTES:
                raise ValidationError(
                    f"request body of {length} bytes exceeds the "
                    f"{MAX_REQUEST_BODY_BYTES}-byte limit"
                )
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = jsonutil.loads(raw)
            except ValueError as exc:
                raise ValidationError(f"request body is not valid JSON: {exc}") from exc
            if not isinstance(data, dict):
                raise ValidationError("request body must be a JSON object")
            return data

        def _dispatch(self, routes: list[tuple[str, Callable[[], None]]]) -> None:
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            for route_path, handler in routes:
                if route_path == path:
                    try:
                        handler()
                    except AccountSvcError as exc:
                        self._send_json(_status_for(exc), {"error": str(exc)})
                    except Exception as exc:  # pragma: no cover - defensive
                        self._send_json(500, {"error": f"internal error: {exc}"})
                    return
            self._send_json(404, {"error": f"no route for {self.command} {path}"})

        # -- unauthenticated recovery flow -------------------------------

        def _handle_recovery_start(self) -> None:
            body = self._read_json()
            org_id = _require_str(body, "organization")
            email = _require_str(body, "email")
            result = recovery_service.start(org_id, email)
            self._send_json(202, result)

        def _handle_recovery_complete(self) -> None:
            body = self._read_json()
            token = _require_str(body, "token")
            result = recovery_service.complete(token)
            self._send_json(200, result)

        # -- authenticated administration ---------------------------------

        def _handle_notifications_retry(self) -> None:
            require_auth(self.headers)
            body = self._read_json()
            if body:
                raise ValidationError(
                    "recovery notification retry accepts no request fields; "
                    "it always processes every eligible notice"
                )
            result = recovery_service.retry_notifications()
            self._send_json(200, result)

        def _handle_admin_get_account(self, account_id: str) -> None:
            require_auth(self.headers)
            self._send_json(200, _account_view(repository, account_id))

        def _handle_admin_get_ticket(self, ticket_id: str) -> None:
            require_auth(self.headers)
            self._send_json(200, _ticket_view(repository, ticket_id))

        def _handle_admin_get_request(self, request_id: str) -> None:
            require_auth(self.headers)
            self._send_json(200, _request_view(repository, request_id))

        def _handle_admin_create_ticket(self) -> None:
            require_auth(self.headers)
            body = self._read_json()
            ticket = repository.create_ticket(
                linked_request_id=_require_str(body, "linked_request_id"),
                subject=_require_str(body, "subject"),
                operator_id=_require_str(body, "operator_id"),
            )
            self._send_json(201, ticket)

        def _handle_admin_create_operator(self) -> None:
            require_auth(self.headers)
            body = self._read_json()
            operator = repository.create_operator(_require_str(body, "display_name"))
            self._send_json(201, operator)

        def _handle_admin_assign_operator_role(self) -> None:
            require_auth(self.headers)
            body = self._read_json()
            assignment = repository.assign_operator_role(
                operator_id=_require_str(body, "operator_id"),
                org_id=_require_str(body, "organization"),
                role=_require_str(body, "role"),
            )
            self._send_json(200, assignment)

        def _handle_admin_revoke_operator_role(self) -> None:
            require_auth(self.headers)
            body = self._read_json()
            assignment = repository.revoke_operator_role(
                operator_id=_require_str(body, "operator_id"),
                org_id=_require_str(body, "organization"),
            )
            self._send_json(200, assignment)

        def _handle_stage_request_retry(self, request_id: str) -> None:
            require_auth(self.headers)
            body = self._read_json()
            _reject_disallowed_staging_fields(body)
            staging = recovery_service.stage_single_retry(
                request_id=request_id,
                operator_id=_require_str(body, "operator_id"),
            )
            self._send_json(201, staging)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            parts = [p for p in path.split("/") if p]
            if (
                len(parts) == 4
                and parts[0] == "recovery"
                and parts[1] == "requests"
                and parts[3] == "retry"
            ):
                request_id = parts[2]
                self._dispatch(
                    [(path, lambda: self._handle_stage_request_retry(request_id))]
                )
                return
            if path == "/admin/tickets":
                self._dispatch([(path, self._handle_admin_create_ticket)])
                return
            if path == "/admin/operators":
                self._dispatch([(path, self._handle_admin_create_operator)])
                return
            if path == "/admin/operator-roles":
                self._dispatch([(path, self._handle_admin_assign_operator_role)])
                return
            if path == "/admin/operator-roles/revoke":
                self._dispatch([(path, self._handle_admin_revoke_operator_role)])
                return
            self._dispatch(
                [
                    ("/recovery/start", self._handle_recovery_start),
                    ("/recovery/complete", self._handle_recovery_complete),
                    (
                        "/recovery/notifications/retry",
                        self._handle_notifications_retry,
                    ),
                ]
            )

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[0] == "admin" and parts[1] == "accounts":
                account_id = parts[2]
                self._dispatch(
                    [(path, lambda: self._handle_admin_get_account(account_id))]
                )
                return
            if len(parts) == 3 and parts[0] == "admin" and parts[1] == "tickets":
                ticket_id = parts[2]
                self._dispatch(
                    [(path, lambda: self._handle_admin_get_ticket(ticket_id))]
                )
                return
            if len(parts) == 3 and parts[0] == "admin" and parts[1] == "requests":
                request_id = parts[2]
                self._dispatch(
                    [(path, lambda: self._handle_admin_get_request(request_id))]
                )
                return
            self._send_json(404, {"error": f"no route for GET {path}"})

    return Handler


def _require_str(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{key!r} is required")
    return value


class LoopbackHTTPServer(http.server.HTTPServer):
    """Single-threaded on purpose: requests share one sqlite connection and
    are handled one at a time, so no additional locking is needed.
    """

    allow_reuse_address = True


def build_server(
    repository: Repository,
    recovery_service: RecoveryService,
    bearer_token: str,
    host: str = "127.0.0.1",
    port: int = 0,
) -> LoopbackHTTPServer:
    handler_cls = make_handler(repository, recovery_service, bearer_token)
    return LoopbackHTTPServer((host, port), handler_cls)
