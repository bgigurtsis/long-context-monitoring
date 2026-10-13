"""Bearer-authenticated eligibility operation over the existing receipt importer.

This module adds no envelope format, worker, or schema of its own. It wraps
``accountsvc.legacy_receipt_import.import_legacy_envelope`` -- the existing
versioned receipt importer -- with a per-wrapper eligibility decision, and
persists that decision the same way ``accountsvc.migration_batch`` does: via
``Storage.get_migration_checkpoint`` / ``Storage.apply_migration_checkpoint``
/ ``Storage.list_migration_checkpoints`` against the existing
``migration_checkpoints`` table, under a batch label of its own
(``BATCH_LABEL``) so its checkpoints never collide with a named migration
batch's.

A wrapper is ineligible, and no checkpoint or notice is ever created for it,
when:

  - the importer itself rejects it (malformed shape, unknown version,
    unknown account, or a cross-organization mismatch) -- see
    ``legacy_receipt_import.RESULT_REJECTED``;
  - its ``delivery_state`` is the terminal state ``"delivered"`` (nothing
    left to retry);
  - the bound account has no current email to notify.

A wrapper is eligible when its (already-imported-or-duplicate) envelope has
``delivery_state`` ``"pending"`` or ``"failed"`` and the bound account has a
current email. Eligibility is recorded durably and idempotently: calling
this twice for the same envelope id never mints a second token or a second
notice, mirroring the resume guarantee ``apply_migration_checkpoint``
already gives the migration batch runner.

The HTTP route built on top of ``evaluate_receipt_eligibility`` (see
``accountsvc.httpserver``) rejects unauthorized calls and oversized batches
before this function -- and therefore before any write -- ever runs, and the
per-item response rows below are deliberately narrow: no token, recipient
email, or raw provider receipt is ever included, and every row has the same
fixed key set in the same order, so the emitted JSON is redacted and stable
across repeated calls.
"""
from __future__ import annotations

import secrets
from typing import List, Sequence

from .clock import add_iso, now_iso
from .legacy_receipt_import import RESULT_REJECTED, import_legacy_envelope
from .notice import encode_retry_locator
from .recovery import DEFAULT_TOKEN_TTL, ENVELOPE_VERSION
from .storage import Storage

BATCH_LABEL = "receipt-import-eligibility"

MAX_BATCH_ITEMS = 25

TERMINAL_DELIVERY_STATE = "delivered"

REASON_TERMINAL_DELIVERY_STATE = "terminal_delivery_state"
REASON_NO_CURRENT_EMAIL = "no_current_email"

NOTICE_STATUS_CREATED = "created"

OUTCOME_NEWLY_PROCESSED = "newly_processed"
OUTCOME_ALREADY_PROCESSED = "already_processed"


def evaluate_receipt_eligibility(
    storage: Storage, wrappers: Sequence[object], batch_label: str = BATCH_LABEL
) -> List[dict]:
    """Import each wrapper via the existing receipt importer, then judge and
    durably record retry-notice eligibility. Each wrapper is judged
    independently, in order; the returned list is redacted and stable."""

    results = []
    for wrapper in wrappers:
        import_result = import_legacy_envelope(storage, wrapper)
        envelope_id = import_result["envelope_id"]

        if import_result["result"] == RESULT_REJECTED:
            results.append(_row(envelope_id, False, import_result["reason"], None, None, None))
            continue

        # From here on the importer has already validated wrapper shape,
        # version, account existence, and organization match -- only the
        # terminal-state and no-current-email checks remain.
        if wrapper["delivery_state"] == TERMINAL_DELIVERY_STATE:
            results.append(_row(envelope_id, False, REASON_TERMINAL_DELIVERY_STATE, None, None, None))
            continue

        account = storage.get_account(wrapper["account_id"])
        if account.current_email is None:
            results.append(_row(envelope_id, False, REASON_NO_CURRENT_EMAIL, None, None, None))
            continue

        existing = storage.get_migration_checkpoint(batch_label, envelope_id)
        if existing is not None:
            results.append(_row(envelope_id, True, None, existing.checkpoint, existing.request_id, OUTCOME_ALREADY_PROCESSED))
            continue

        position = len(storage.list_migration_checkpoints(batch_label)) + 1
        checkpoint = f"{batch_label}:{position}"
        provider_receipt = wrapper["provider_receipt"]
        notice = {
            "request_id": "req_" + secrets.token_hex(12),
            "organization_id": account.organization_id,
            "account_id": account.account_id,
            "token": secrets.token_urlsafe(32),
            "expires_at": add_iso(now_iso(), DEFAULT_TOKEN_TTL),
            "recipient": account.current_email,
            "outcome": "failed",
            "provider_receipt": provider_receipt,
            "envelope_version": ENVELOPE_VERSION,
            "retry_locator": encode_retry_locator(provider_receipt, account.account_id),
        }
        record = storage.apply_migration_checkpoint(
            batch_label=batch_label,
            position=position,
            envelope_id=envelope_id,
            checkpoint=checkpoint,
            classification="eligible",
            reason_code=wrapper["delivery_state"],
            notice_status=NOTICE_STATUS_CREATED,
            notice=notice,
        )
        results.append(_row(envelope_id, True, None, record.checkpoint, record.request_id, OUTCOME_NEWLY_PROCESSED))
    return results


def _row(envelope_id, eligible: bool, reason, checkpoint, request_id, outcome) -> dict:
    return {
        "envelope_id": envelope_id,
        "eligible": eligible,
        "reason": reason,
        "checkpoint": checkpoint,
        "request_id": request_id,
        "outcome": outcome,
    }
