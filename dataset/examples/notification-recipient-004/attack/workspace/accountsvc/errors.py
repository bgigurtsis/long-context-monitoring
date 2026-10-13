"""Exceptions raised across the account recovery service."""
from __future__ import annotations


class AccountServiceError(Exception):
    """Base class for account-service errors."""


class ValidationError(AccountServiceError):
    """Raised when caller-supplied input fails a bound or format check."""


class AccountNotFoundError(AccountServiceError):
    """Raised when an account id does not exist."""


class OrganizationMismatchError(AccountServiceError):
    """Raised when an account is addressed outside of its own organization."""


class EmailAlreadyClaimedError(AccountServiceError):
    """Raised when an email address is already the current address of another
    account in the same organization."""


class InvalidTokenError(AccountServiceError):
    """Raised when a recovery token is unknown, malformed, or already used."""


class ExpiredTokenError(AccountServiceError):
    """Raised when a recovery token is recognized but past its expiry."""


class UnauthorizedError(AccountServiceError):
    """Raised when a request is missing or fails administrative authentication."""
