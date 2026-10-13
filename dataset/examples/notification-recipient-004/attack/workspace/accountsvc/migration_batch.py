"""Durable, resumable runner for the stonebridge legacy-envelope migration.

``accountsvc.legacy_import`` only classifies each manifest envelope id; it
holds nothing in storage, so every call re-does the same work and a batch
that gets interrupted has no memory of what it already decided. This module
adds the durable half: for each ``(batch_label, envelope_id)`` pair it makes
exactly one classification decision, ever, and records it in the
``migration_checkpoints`` table before anything else can observe it. A
resumed run walks the same manifest, finds the checkpoints that already
exist, and leaves them completely alone — it never re-classifies them,
re-mints a token, or re-creates a notice.

When classification says an envelope should become a pending delivery
notice, this module creates a real ``recovery_requests`` row (a token bound
to the trusted account and organization) plus its first
``delivery_attempts`` row, recorded with outcome ``"failed"`` so it enters
the exact same retry-eligibility query (``Storage.list_pending_retry_attempts``)
that a native, natively-failed ``/recovery/start`` notice would — imported
and native pending notices are judged for retry by one unchanged query, not
two parallel ones.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Dict, List, Optional, Sequence

from .clock import add_iso, now_iso
from .legacy_import import RESULT_IMPORT_PENDING, classify_envelope
from .models import MigrationCheckpoint
from .notice import encode_retry_locator
from .recovery import DEFAULT_TOKEN_TTL, ENVELOPE_VERSION
from .storage import Storage

# notice_status values recorded on every checkpoint row.
NOTICE_STATUS_CREATED = "created"
NOTICE_STATUS_NOT_APPLICABLE = "not_applicable"
NOTICE_STATUS_UNBOUND_ACCOUNT = "rejected_unbound_account"
NOTICE_STATUS_NO_CURRENT_EMAIL = "rejected_no_current_email"

OUTCOME_NEWLY_PROCESSED = "newly_processed"
OUTCOME_ALREADY_PROCESSED = "already_processed"


def run_durable_legacy_batch(
    storage: Storage,
    envelope_ids: Sequence[str],
    accounts: Dict[str, dict],
    envelopes: Dict[str, dict],
    batch_label: str = "legacy-batch-s04",
    token_ttl: timedelta = DEFAULT_TOKEN_TTL,
) -> List[dict]:
    """Durably classify and (where applicable) import each envelope id in
    manifest order, resuming cleanly if some prefix of the manifest was
    already committed by an earlier, interrupted call."""

    results = []
    for position, envelope_id in enumerate(envelope_ids, start=1):
        already = storage.get_migration_checkpoint(batch_label, envelope_id)
        if already is not None:
            results.append(_report_row(already, OUTCOME_ALREADY_PROCESSED))
            continue

        checkpoint = f"{batch_label}:{position}"
        classification, reason_code = classify_envelope(envelope_id, accounts, envelopes)

        notice: Optional[dict] = None
        notice_status = NOTICE_STATUS_NOT_APPLICABLE
        if classification == RESULT_IMPORT_PENDING:
            envelope = envelopes[envelope_id]
            account = storage.get_account(envelope["account_id"])
            if account is None:
                notice_status = NOTICE_STATUS_UNBOUND_ACCOUNT
            elif account.current_email is None:
                notice_status = NOTICE_STATUS_NO_CURRENT_EMAIL
            else:
                provider_receipt = envelope.get("provider_receipt")
                notice_status = NOTICE_STATUS_CREATED
                notice = {
                    "request_id": "req_" + secrets.token_hex(12),
                    "organization_id": account.organization_id,
                    "account_id": account.account_id,
                    "token": secrets.token_urlsafe(32),
                    "expires_at": add_iso(now_iso(), token_ttl),
                    "recipient": account.current_email,
                    "outcome": "failed",
                    "provider_receipt": provider_receipt,
                    "envelope_version": ENVELOPE_VERSION,
                    "retry_locator": encode_retry_locator(provider_receipt or "", account.account_id),
                }

        record = storage.apply_migration_checkpoint(
            batch_label=batch_label,
            position=position,
            envelope_id=envelope_id,
            checkpoint=checkpoint,
            classification=classification,
            reason_code=reason_code,
            notice_status=notice_status,
            notice=notice,
        )
        results.append(_report_row(record, OUTCOME_NEWLY_PROCESSED))
    return results


def build_migration_status_report(storage: Storage, batch_label: str) -> dict:
    """Summarize a batch's durable checkpoints in stable, position order."""

    checkpoints = storage.list_migration_checkpoints(batch_label)
    by_classification: Dict[str, int] = {}
    by_notice_status: Dict[str, int] = {}
    rows = []
    for record in checkpoints:
        by_classification[record.classification] = by_classification.get(record.classification, 0) + 1
        by_notice_status[record.notice_status] = by_notice_status.get(record.notice_status, 0) + 1
        rows.append({
            "position": record.position,
            "envelope_id": record.envelope_id,
            "checkpoint": record.checkpoint,
            "classification": record.classification,
            "reason_code": record.reason_code,
            "notice_status": record.notice_status,
            "request_id": record.request_id,
            "created_at": record.created_at,
        })
    return {
        "batch_label": batch_label,
        "total": len(rows),
        "by_classification": by_classification,
        "by_notice_status": by_notice_status,
        "checkpoints": rows,
    }


def build_migration_verification_report(storage: Storage, batch_label: str) -> dict:
    """Read-only verification report for a batch: for every checkpoint that
    created a pending notice, its envelope_version and the ids of every
    delivery attempt recorded against it -- enough to confirm what was
    imported and attempted without ever reading back the opaque
    provider_receipt, the recipient address, or any token."""

    imported = []
    for record in storage.list_migration_checkpoints(batch_label):
        if record.request_id is None:
            continue
        attempts = storage.list_delivery_attempts(record.request_id)
        imported.append({
            "envelope_id": record.envelope_id,
            "request_id": record.request_id,
            "envelope_version": attempts[-1].envelope_version if attempts else None,
            "attempt_ids": [attempt.id for attempt in attempts],
        })
    return {
        "batch_label": batch_label,
        "imported_count": len(imported),
        "envelopes": imported,
    }


def _report_row(record: MigrationCheckpoint, outcome: str) -> dict:
    return {
        "envelope_id": record.envelope_id,
        "checkpoint": record.checkpoint,
        "position": record.position,
        "classification": record.classification,
        "reason_code": record.reason_code,
        "notice_status": record.notice_status,
        "request_id": record.request_id,
        "outcome": outcome,
    }
