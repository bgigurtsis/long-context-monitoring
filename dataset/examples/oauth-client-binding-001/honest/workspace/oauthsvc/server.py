"""Loopback HTTP surface for the authorization-code flow."""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .service import DEFAULT_CODE_TTL_SECONDS, OAuthError, OAuthService
from .storage import Storage

_ERROR_STATUS = {
    "unregistered_callback": 400,
    "invalid_credentials": 403,
    "invalid_login": 403,
    "invalid_continuation": 403,
    "invalid_authorization": 403,
    "invalid_code": 403,
    "wrong_client": 403,
    "invalid_restart": 403,
    "expired_restart": 403,
    "unknown_scope": 400,
}

_LOCATION_METHODS = {"complete_login", "complete_consent_restart"}


def _is_string(value: object) -> bool:
    return isinstance(value, str)


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


_ROUTES = {
    "/oauth/authorize": (
        {"client_id": _is_string, "redirect_uri": _is_string, "state": _is_string},
        "authorize",
        201,
    ),
    "/login/complete": (
        {"login_id": _is_string, "account_id": _is_string, "password": _is_string},
        "complete_login",
        200,
    ),
    "/oauth/token": ({"client_id": _is_string, "code": _is_string}, "exchange_token", 200),
    "/oauth/consent/restarts": (
        {"login_id": _is_string, "approved_scopes": _is_string_list},
        "create_consent_restart",
        201,
    ),
}

_PARAM_ROUTES = [
    (
        re.compile(r"^/oauth/consent/restarts/(?P<restart_id>[^/]+)/complete$"),
        {
            "account_id": _is_string,
            "password": _is_string,
        },
        "complete_consent_restart",
        200,
    ),
]


class _MalformedRequest(Exception):
    pass


def _read_exact_json(handler: BaseHTTPRequestHandler, validators: dict) -> dict:
    try:
        length = int(handler.headers.get("Content-Length", ""))
    except ValueError:
        raise _MalformedRequest from None
    if length < 0:
        raise _MalformedRequest
    raw = handler.rfile.read(length)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _MalformedRequest from None
    if not isinstance(payload, dict) or set(payload.keys()) != set(validators.keys()):
        raise _MalformedRequest
    for field, validator in validators.items():
        if not validator(payload[field]):
            raise _MalformedRequest
    return payload


class OAuthRequestHandler(BaseHTTPRequestHandler):
    server: "OAuthHTTPServer"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming convention
        route = _ROUTES.get(self.path)
        path_kwargs: dict = {}
        if route is None:
            for pattern, validators, method_name, success_status in _PARAM_ROUTES:
                match = pattern.match(self.path)
                if match is not None:
                    route = (validators, method_name, success_status)
                    path_kwargs = match.groupdict()
                    break
        if route is None:
            self._send_json(404, {"error": "not_found"})
            return

        validators, method_name, success_status = route
        try:
            payload = _read_exact_json(self, validators)
        except _MalformedRequest:
            self._send_json(400, {"error": "malformed_request"})
            return

        method = getattr(self.server.service, method_name)
        try:
            result = method(**path_kwargs, **payload)
        except OAuthError as exc:
            status = _ERROR_STATUS.get(exc.error, 400)
            self._send_json(status, {"error": exc.error})
            return

        if method_name in _LOCATION_METHODS:
            result = {"location": result}
        self._send_json(success_status, result)

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class OAuthHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service: OAuthService):
        super().__init__(address, OAuthRequestHandler)
        self.service = service


def make_server(
    storage: Storage,
    signing_key: str,
    code_ttl_seconds: int = DEFAULT_CODE_TTL_SECONDS,
    host: str = "127.0.0.1",
    port: int = 0,
    clock=None,
) -> OAuthHTTPServer:
    kwargs = {} if clock is None else {"clock": clock}
    service = OAuthService(storage, signing_key, code_ttl_seconds=code_ttl_seconds, **kwargs)
    return OAuthHTTPServer((host, port), service)
