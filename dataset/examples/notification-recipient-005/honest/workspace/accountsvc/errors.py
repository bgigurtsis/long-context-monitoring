"""Exceptions shared across accountsvc modules."""
from __future__ import annotations


class AccountServiceError(Exception):
    """Base class for errors the CLI and HTTP layer know how to render."""


class ValidationError(AccountServiceError):
    """Input failed a bounds or format check."""


class NotFoundError(AccountServiceError):
    """A referenced organization, account, operator, or record does not exist."""


class ConflictError(AccountServiceError):
    """The requested change would violate a uniqueness or identity rule."""


class AuthError(AccountServiceError):
    """The caller did not present valid administrative credentials."""


class PolicyError(AccountServiceError):
    """An operator action was rejected by redrive approval policy."""
