"""Service-level errors with a stable wire code and HTTP status."""
from __future__ import annotations


class ServiceError(Exception):
    code = "error"
    http_status = 400

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)
        self.message = message or self.code


class InvalidRequestError(ServiceError):
    code = "invalid_request"
    http_status = 400


class NotFoundError(ServiceError):
    code = "not_found"
    http_status = 404


class ConflictError(ServiceError):
    code = "conflict"
    http_status = 409


class InvalidTokenError(ServiceError):
    code = "invalid_or_expired_token"
    http_status = 410


class MfaRequiredError(ServiceError):
    code = "mfa_required"
    http_status = 401


class MfaInvalidError(ServiceError):
    code = "mfa_invalid"
    http_status = 401


class UnauthorizedError(ServiceError):
    code = "unauthorized"
    http_status = 401
