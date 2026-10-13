"""Loopback HTTP surface for the account recovery service.

POST /recovery/start and POST /recovery/complete are reachable by a user
who has already lost access (no bearer token required). POST
/recovery/notifications/retry, POST /reconciliation/import, POST
/reconciliation/status, POST /reconciliation/unresolved, and POST
/reconciliation/export are administrative actions and always require the
configured bearer token.
"""
from __future__ import annotations

import dataclasses
import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from . import models, recovery
from .reconciliation import ReconciliationEngine
from .recovery import RecoveryService
from .storage import ConflictError, NotFoundError, ValidationError

MAX_BODY_BYTES = 16_384


class AccountRecoveryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address,
        handler_cls,
        *,
        recovery_service: RecoveryService,
        bearer_token: str,
        reconciliation_engine: Optional[ReconciliationEngine] = None,
    ) -> None:
        super().__init__(address, handler_cls)
        self.recovery_service = recovery_service
        self.bearer_token = bearer_token
        self.reconciliation_engine = reconciliation_engine


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    server: AccountRecoveryServer

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass  # Keep loopback test/service runs quiet; errors still raise.

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        if self.path == "/recovery/start":
            self._handle_start()
        elif self.path == "/recovery/complete":
            self._handle_complete()
        elif self.path == "/recovery/notifications/retry":
            self._handle_retry()
        elif self.path == "/reconciliation/import":
            self._handle_reconciliation_import()
        elif self.path == "/reconciliation/status":
            self._handle_reconciliation_status()
        elif self.path == "/reconciliation/unresolved":
            self._handle_reconciliation_unresolved()
        elif self.path == "/reconciliation/export":
            self._handle_reconciliation_export()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def _read_body(self) -> Optional[dict]:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            self._send_json(HTTPStatus.LENGTH_REQUIRED, {"error": "content_length_required"})
            return None
        try:
            length = int(length_header)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return None
        if length < 0 or length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body_too_large"})
            return None
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return None
        if not isinstance(parsed, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_body"})
            return None
        return parsed

    def _is_authenticated(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        supplied = header[len(prefix):]
        return hmac.compare_digest(supplied, self.server.bearer_token)

    def _handle_start(self) -> None:
        body = self._read_body()
        if body is None:
            return
        try:
            organization = body["organization"]
            email = body["email"]
        except KeyError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "organization_and_email_required"})
            return
        try:
            result = self.server.recovery_service.start_recovery(organization_id=organization, email=email)
        except ValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(
            HTTPStatus.ACCEPTED,
            {"request_id": result.request_id, "delivery_status": result.delivery_status},
        )

    def _handle_complete(self) -> None:
        body = self._read_body()
        if body is None:
            return
        try:
            token = body["token"]
        except KeyError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "token_required"})
            return
        try:
            result = self.server.recovery_service.complete_recovery(token=token)
        except (recovery.TokenInvalidError, recovery.TokenExpiredError, recovery.TokenAlreadyUsedError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except ValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(
            HTTPStatus.OK,
            {"status": "completed", "account_id": result.account_id, "organization_id": result.organization_id},
        )

    def _handle_retry(self) -> None:
        if not self._is_authenticated():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        body = self._read_body()
        if body is None:
            return
        notification_id = body.get("notification_id")
        try:
            if notification_id is not None:
                if not self._is_eligible_for_named_retry(notification_id):
                    self._send_json(
                        HTTPStatus.CONFLICT,
                        {"error": f"notification {notification_id!r} is not an eligible unresolved delayed delivery"},
                    )
                    return
                updated = self.server.recovery_service.retry_notifications([notification_id])
            else:
                updated = self.server.recovery_service.retry_pending_notifications()
        except NotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        except ConflictError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "notifications": [
                    {"notification_id": n.notification_id, "delivery_state": n.delivery_state}
                    for n in updated
                ]
            },
        )

    def _is_eligible_for_named_retry(self, notification_id: str) -> bool:
        """Gate a caller-named retry against reconciliation's own view.

        A notification reconciliation classifies as still_pending or
        delivered must be refused here, before retry_notifications ever
        runs, so a still-live delayed delivery cannot be forced into a
        premature retry. A notification reconciliation does not track at
        all -- the ordinary FAILED/RETRYING compatibility path, or an
        ACCEPTED_DELAYED one on a server with no reconciliation engine
        configured -- is left for retry_notifications' own delivery-state
        check to accept or refuse; no reconciliation classification is a
        prerequisite for that path.
        """
        if self.server.reconciliation_engine is None:
            return True
        for classification in self.server.reconciliation_engine.classify_delayed_attempts():
            if classification.notification_id == notification_id:
                return classification.status == models.DelayedAttemptStatus.UNRESOLVED
        return True

    def _handle_reconciliation_import(self) -> None:
        if not self._is_authenticated():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if self.server.reconciliation_engine is None:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "reconciliation_not_configured"})
            return
        body = self._read_body()
        if body is None:
            return
        observations = body.get("observations")
        if not isinstance(observations, list):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "observations_must_be_a_list"})
            return
        feed_id = body.get("feed_id")
        page_number = body.get("page_number")
        if (feed_id is None) != (page_number is None):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "feed_id_and_page_number_required_together"})
            return
        try:
            if feed_id is None:
                results = self.server.reconciliation_engine.ingest_feed(observations, now=body.get("now"))
                payload = {"results": [dataclasses.asdict(r) for r in results]}
            else:
                page_result = self.server.reconciliation_engine.ingest_page(
                    feed_id=feed_id, page_number=page_number, observations=observations, now=body.get("now")
                )
                payload = {
                    "feed_id": page_result.feed_id,
                    "page_number": page_result.page_number,
                    "committed_page": page_result.committed_page,
                    "skipped": page_result.skipped,
                    "results": [dataclasses.asdict(r) for r in page_result.results],
                }
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"malformed_observation: {exc}"})
            return
        except NotFoundError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, payload)

    def _handle_reconciliation_status(self) -> None:
        if not self._is_authenticated():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if self.server.reconciliation_engine is None:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "reconciliation_not_configured"})
            return
        body = self._read_body()
        if body is None:
            return
        classifications = self.server.reconciliation_engine.classify_delayed_attempts(now=body.get("now"))
        self._send_json(HTTPStatus.OK, {"attempts": [dataclasses.asdict(c) for c in classifications]})

    def _handle_reconciliation_unresolved(self) -> None:
        if not self._is_authenticated():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if self.server.reconciliation_engine is None:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "reconciliation_not_configured"})
            return
        body = self._read_body()
        if body is None:
            return
        feed_id = body.get("feed_id")
        if not isinstance(feed_id, str) or not feed_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "feed_id_required"})
            return
        try:
            batch = self.server.reconciliation_engine.select_unresolved(
                feed_id=feed_id, limit=body.get("limit"), now=body.get("now")
            )
        except ValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        payload = {
            "feed_id": batch.feed_id,
            "offset": batch.offset,
            "next_offset": batch.next_offset,
            "attempts": [dataclasses.asdict(a) for a in batch.attempts],
        }
        self._send_json(HTTPStatus.OK, payload, sort_keys=True)

    def _handle_reconciliation_export(self) -> None:
        if not self._is_authenticated():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if self.server.reconciliation_engine is None:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "reconciliation_not_configured"})
            return
        body = self._read_body()
        if body is None:
            return
        rows = self.server.reconciliation_engine.export_status(now=body.get("now"))
        self._send_json(HTTPStatus.OK, {"attempts": [dataclasses.asdict(r) for r in rows]}, sort_keys=True)

    def _send_json(self, status: HTTPStatus, payload: dict, *, sort_keys: bool = False) -> None:
        body = json.dumps(payload, sort_keys=sort_keys).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(
    *,
    host: str,
    port: int,
    recovery_service: RecoveryService,
    bearer_token: str,
    reconciliation_engine: Optional[ReconciliationEngine] = None,
) -> AccountRecoveryServer:
    return AccountRecoveryServer(
        (host, port),
        RecoveryRequestHandler,
        recovery_service=recovery_service,
        bearer_token=bearer_token,
        reconciliation_engine=reconciliation_engine,
    )
