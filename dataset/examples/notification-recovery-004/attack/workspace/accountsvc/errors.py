"""Exception types shared across the account recovery service."""
from __future__ import annotations


class AccountSvcError(Exception):
    """Base error for all service-level failures."""


class NotFoundError(AccountSvcError):
    """A referenced entity does not exist."""


class ConflictError(AccountSvcError):
    """An operation would violate a durable uniqueness rule."""


class ValidationError(AccountSvcError):
    """Caller-supplied input failed validation."""


class AuthenticationError(AccountSvcError):
    """A caller failed to authenticate for an administrative action."""


class AuthorizationError(AccountSvcError):
    """An authenticated caller is not permitted to perform this action."""


class RateLimitError(AccountSvcError):
    """A caller has exceeded a rate limit on a support action."""
