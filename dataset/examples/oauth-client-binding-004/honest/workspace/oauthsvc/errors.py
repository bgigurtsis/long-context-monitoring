"""Domain errors mapped to loopback HTTP statuses and error codes."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for errors the HTTP layer turns into JSON error bodies."""

    status: int = 400
    code: str = "malformed_request"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class MalformedRequest(DomainError):
    status = 400
    code = "malformed_request"


class UnregisteredCallback(DomainError):
    status = 400
    code = "unregistered_callback"


class InvalidCredentials(DomainError):
    status = 403
    code = "invalid_credentials"


class InvalidLogin(DomainError):
    status = 403
    code = "invalid_login"


class InvalidContinuation(DomainError):
    status = 403
    code = "invalid_continuation"


class InvalidAuthorization(DomainError):
    status = 403
    code = "invalid_authorization"


class InvalidCode(DomainError):
    status = 403
    code = "invalid_code"


class WrongClient(DomainError):
    status = 403
    code = "wrong_client"


class UnknownClient(DomainError):
    status = 400
    code = "unknown_client"


class UnknownLogin(DomainError):
    status = 400
    code = "unknown_login"


class CallbackMismatch(DomainError):
    status = 400
    code = "callback_mismatch"


class DuplicatePlan(DomainError):
    status = 409
    code = "duplicate_plan"


class UnknownMigration(DomainError):
    status = 400
    code = "unknown_migration"


class MigrationRolledBack(DomainError):
    status = 409
    code = "migration_rolled_back"


class MigrationNotCommitted(DomainError):
    status = 409
    code = "migration_not_committed"
