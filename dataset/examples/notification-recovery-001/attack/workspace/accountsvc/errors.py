"""Exception types shared across the account recovery service."""
from __future__ import annotations


class AccountSvcError(Exception):
    """Base class for all account-recovery domain errors."""


class ValidationError(AccountSvcError):
    """Raised when caller-supplied data fails bounded validation."""


class ConflictError(AccountSvcError):
    """Raised when an operation would violate a uniqueness rule."""


class NotFoundError(AccountSvcError):
    """Raised when a referenced organization, account, or request is missing."""


class RecoveryError(AccountSvcError):
    """Raised when a recovery token is invalid, expired, or already used."""


class AuthError(AccountSvcError):
    """Raised when an administrative request fails authentication."""
