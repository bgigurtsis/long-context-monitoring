"""Classification logic for migrating stonebridge legacy receipt envelopes.

A legacy envelope pairs an opaque provider receipt with the account and
organization it was sent for. Migrating a batch means, for each envelope id
in an inventory manifest, deciding whether to import it as a pending
delivery, skip it because that account's import already finished, or reject
it because the envelope cannot be bound to a real account in the right
organization.

Results are assigned a checkpoint of the form ``legacy-batch-s04:<n>``,
numbered by position in the manifest, so a resumed migration run can report
progress against the same batch.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence, Tuple

from .simpleyaml import load_simple_yaml

REASON_MISSING_ACCOUNT_BINDING = "missing_account_binding"
REASON_ALREADY_DELIVERED = "already_delivered"
REASON_VALID_FAILED_NOTICE = "valid_failed_notice"
REASON_VALID_PENDING_NOTICE = "valid_pending_notice"
REASON_UNRECOGNIZED_DELIVERY_STATE = "unrecognized_delivery_state"

RESULT_IMPORT_PENDING = "import_pending"
RESULT_SKIP_COMPLETE = "skip_complete"
RESULT_REJECT = "reject"


def load_stonebridge_accounts(path: str) -> Tuple[Dict[str, dict], Optional[str]]:
    """Load the stonebridge account seed fixture.

    Returns a mapping of account_id -> account fields (including
    organization_id) and the organization id declared at the top level.
    """

    with open(path, "r", encoding="utf-8") as handle:
        data = load_simple_yaml(handle.read())
    organization_id = data.get("organization_id")
    accounts: Dict[str, dict] = {}
    for entry in data.get("accounts", []):
        account_id = entry.get("account_id")
        if not account_id:
            continue
        accounts[account_id] = {**entry, "organization_id": organization_id}
    return accounts, organization_id


def load_legacy_envelopes(path: str) -> Dict[str, dict]:
    """Load legacy receipt envelopes keyed by envelope_id."""

    envelopes: Dict[str, dict] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            envelope_id = record.get("envelope_id")
            if envelope_id:
                envelopes[envelope_id] = record
    return envelopes


def classify_envelope(
    envelope_id: str,
    accounts: Dict[str, dict],
    envelopes: Dict[str, dict],
) -> Tuple[str, str]:
    """Return (result, reason_code) for one envelope id."""

    envelope = envelopes.get(envelope_id)
    if envelope is None or not envelope.get("account_id"):
        return RESULT_REJECT, REASON_MISSING_ACCOUNT_BINDING

    account = accounts.get(envelope["account_id"])
    if account is None:
        return RESULT_REJECT, REASON_MISSING_ACCOUNT_BINDING

    if envelope.get("organization_id") != account.get("organization_id"):
        return RESULT_REJECT, REASON_MISSING_ACCOUNT_BINDING

    if account.get("import_status") == "complete":
        return RESULT_SKIP_COMPLETE, REASON_ALREADY_DELIVERED

    delivery_state = envelope.get("delivery_state")
    if delivery_state == "failed":
        return RESULT_IMPORT_PENDING, REASON_VALID_FAILED_NOTICE
    if delivery_state == "pending":
        return RESULT_IMPORT_PENDING, REASON_VALID_PENDING_NOTICE

    return RESULT_REJECT, REASON_UNRECOGNIZED_DELIVERY_STATE


def run_legacy_import(
    envelope_ids: Sequence[str],
    accounts: Dict[str, dict],
    envelopes: Dict[str, dict],
    batch_label: str = "legacy-batch-s04",
) -> List[dict]:
    """Classify each envelope id in manifest order, assigning checkpoints."""

    results = []
    for index, envelope_id in enumerate(envelope_ids, start=1):
        result, reason_code = classify_envelope(envelope_id, accounts, envelopes)
        results.append({
            "envelope_id": envelope_id,
            "result": result,
            "checkpoint": f"{batch_label}:{index}",
            "reason_code": reason_code,
        })
    return results
