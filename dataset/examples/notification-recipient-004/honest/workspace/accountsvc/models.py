"""Data model for the account recovery service.

These are plain read models returned by the storage layer. Storage owns
persistence and constraint enforcement; these dataclasses just give callers
(recovery flow, CLI, tests) a typed shape to work with.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Organization:
    organization_id: str
    created_at: str


@dataclass(frozen=True)
class Account:
    account_id: str
    organization_id: str
    created_at: str
    current_email: Optional[str]
    mfa_enabled: bool


@dataclass(frozen=True)
class AccountEmail:
    account_id: str
    organization_id: str
    email: str
    status: str  # "current" or "released"
    created_at: str
    released_at: Optional[str]


@dataclass(frozen=True)
class MfaFactor:
    account_id: str
    enabled: bool
    updated_at: str


@dataclass(frozen=True)
class RecoveryRequest:
    request_id: str
    organization_id: str
    account_id: str
    token: str
    created_at: str
    expires_at: str
    used_at: Optional[str]
    status: str  # "pending", "completed", or "expired"


@dataclass(frozen=True)
class DeliveryAttempt:
    id: int
    recovery_request_id: str
    attempt_number: int
    account_id: str  # trusted binding: the recovery request's own account_id
    recipient: str
    outcome: str  # "sent" or "failed"
    provider_receipt: Optional[str]
    envelope_version: int
    retry_locator: Optional[str]
    created_at: str


@dataclass(frozen=True)
class ReceiptEnvelope:
    envelope_id: str
    organization_id: str
    account_id: str
    provider_receipt: str
    delivery_state: str
    created_at: str


@dataclass(frozen=True)
class MigrationCheckpoint:
    batch_label: str
    envelope_id: str
    checkpoint: str
    position: int
    classification: str
    reason_code: str
    notice_status: str  # "created" or a not-created reason (see migration_batch)
    request_id: Optional[str]  # set only when notice_status == "created"
    created_at: str
