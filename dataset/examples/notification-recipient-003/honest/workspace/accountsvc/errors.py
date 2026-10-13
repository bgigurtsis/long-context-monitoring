"""Exceptions shared across the account recovery service."""
from __future__ import annotations


class AccountServiceError(Exception):
    """Base class for errors the CLI and HTTP layer know how to render."""


class ValidationError(AccountServiceError):
    """Input failed a bounded-input check before it reached storage."""


class NotFoundError(AccountServiceError):
    """A referenced organization, account, or request does not exist."""


class ConflictError(AccountServiceError):
    """The requested change would violate a uniqueness or state rule."""


class AuthError(AccountServiceError):
    """The caller did not present a valid bearer token."""


class ForbiddenError(AccountServiceError):
    """The caller authenticated but is not permitted to perform this action."""
