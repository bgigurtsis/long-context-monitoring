"""Versioned importer for legacy receipt envelope wrappers.

A wrapper is one JSON object describing a single legacy receipt envelope:

    {
        "version": 1,
        "envelope_id": "stonebridge-envelope-401",
        "organization_id": "org-stonebridge",
        "account_id": "acct-receipt-a",
        "provider_receipt": "<opaque provider text>",
        "delivery_state": "pending" | "delivered" | "failed"
    }

``version`` selects the wrapper shape this module knows how to read.
``SUPPORTED_ENVELOPE_VERSION`` is the only version this importer accepts;
any other value (missing, wrong type, or simply not one we recognize) is
rejected outright rather than guessed at, so a future format change can add
a new version without silently misreading old or new data as the other.

Trust model: ``account_id`` is looked up against ``Storage`` -- the
service's own record of which account belongs to which organization -- and
that lookup's ``organization_id`` is what gets written. The wrapper's own
``organization_id`` claim is only ever used to *check* against the trusted
value; a mismatch is a rejection (``cross_organization_mismatch``), not a
correction. This mirrors ``account_id_from_retry_locator`` in
``accountsvc.notice``, which likewise never trusts a caller-supplied
binding over the service's own record.

``provider_receipt`` is carried through as opaque text: read as a string,
written as a string, never parsed or interpreted.

Every wrapper is validated in full before any write is attempted, and the
write itself is one atomic INSERT (see
``Storage.insert_receipt_envelope_if_absent``). A rejected wrapper -- for
being malformed, an unknown version, an unknown account, or a
cross-organization mismatch -- never reaches storage at all, so it can
never leave a partial row behind. Each wrapper in a batch is judged
independently: one rejected wrapper does not block the rest of the batch
from importing, and importing the same envelope_id twice is a no-op
(``duplicate``), not a second write or an error.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from .clock import now_iso
from .models import ReceiptEnvelope
from .storage import Storage

SUPPORTED_ENVELOPE_VERSION = 1

REQUIRED_WRAPPER_FIELDS = (
    "version",
    "envelope_id",
    "organization_id",
    "account_id",
    "provider_receipt",
    "delivery_state",
)
VALID_DELIVERY_STATES = ("pending", "delivered", "failed")

RESULT_IMPORTED = "imported"
RESULT_DUPLICATE = "duplicate"
RESULT_REJECTED = "rejected"

REASON_MALFORMED_WRAPPER = "malformed_wrapper"
REASON_UNKNOWN_VERSION = "unknown_version"
REASON_UNKNOWN_ACCOUNT = "unknown_account"
REASON_CROSS_ORGANIZATION = "cross_organization_mismatch"


def _malformed_reason(record: object) -> Optional[str]:
    """Return a rejection reason if the wrapper is missing or misshapes a
    required field; None if it has everything this importer needs to reason
    about further (account lookup, version check, insert)."""

    if not isinstance(record, dict):
        return REASON_MALFORMED_WRAPPER
    for field in REQUIRED_WRAPPER_FIELDS:
        if field not in record:
            return REASON_MALFORMED_WRAPPER
    if not isinstance(record["version"], int) or isinstance(record["version"], bool):
        return REASON_MALFORMED_WRAPPER
    for field in ("envelope_id", "organization_id", "account_id", "provider_receipt"):
        if not isinstance(record[field], str) or not record[field]:
            return REASON_MALFORMED_WRAPPER
    if record["delivery_state"] not in VALID_DELIVERY_STATES:
        return REASON_MALFORMED_WRAPPER
    return None


def import_legacy_envelope(storage: Storage, record: object) -> dict:
    """Import one legacy envelope wrapper.

    Returns {"envelope_id": ..., "result": "imported"|"duplicate"|"rejected",
    "reason": None or a REASON_* code}. Never performs a partial write: a
    rejected wrapper writes nothing at all.
    """

    envelope_id = record.get("envelope_id") if isinstance(record, dict) else None

    reason = _malformed_reason(record)
    if reason is not None:
        return {"envelope_id": envelope_id, "result": RESULT_REJECTED, "reason": reason}

    if record["version"] != SUPPORTED_ENVELOPE_VERSION:
        return {"envelope_id": envelope_id, "result": RESULT_REJECTED, "reason": REASON_UNKNOWN_VERSION}

    # Trusted account binding: organization_id comes from Storage's own
    # account record, never from the wrapper's claim.
    account = storage.get_account(record["account_id"])
    if account is None:
        return {"envelope_id": envelope_id, "result": RESULT_REJECTED, "reason": REASON_UNKNOWN_ACCOUNT}

    if account.organization_id != record["organization_id"]:
        return {"envelope_id": envelope_id, "result": RESULT_REJECTED, "reason": REASON_CROSS_ORGANIZATION}

    envelope = ReceiptEnvelope(
        envelope_id=record["envelope_id"],
        organization_id=account.organization_id,
        account_id=account.account_id,
        provider_receipt=record["provider_receipt"],
        delivery_state=record["delivery_state"],
        created_at=now_iso(),
    )
    inserted = storage.insert_receipt_envelope_if_absent(envelope)
    if not inserted:
        return {"envelope_id": envelope_id, "result": RESULT_DUPLICATE, "reason": None}
    return {"envelope_id": envelope_id, "result": RESULT_IMPORTED, "reason": None}


def import_legacy_envelope_batch(storage: Storage, records: Sequence[object]) -> List[dict]:
    """Import a batch of wrapper records, each judged independently."""

    return [import_legacy_envelope(storage, record) for record in records]
