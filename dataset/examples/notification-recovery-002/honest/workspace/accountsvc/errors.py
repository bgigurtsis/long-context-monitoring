"""Service-level errors mapped to CLI exit codes and HTTP status codes."""
from __future__ import annotations


class ServiceError(Exception):
    """Base error for all recoverable service failures."""

    status_code = 400


class ValidationError(ServiceError):
    status_code = 400


class AuthError(ServiceError):
    status_code = 401


class NotFoundError(ServiceError):
    status_code = 404


class ConflictError(ServiceError):
    status_code = 409
