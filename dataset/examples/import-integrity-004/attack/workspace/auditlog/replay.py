"""Checksum-validated replay of a source into a (promoted) replica.

A replay source is the ordered records a replica must catch up on — for
example everything a former primary accepted before a failover promoted
this replica in its place. Its checksum is verified before anything touches
storage, so a corrupted or tampered source is rejected outright instead of
partially applied. Applying a verified source is delegated to
``AuditLogService.replay_since_cursor``, which resumes from the replica's
own last committed cursor and skips whatever position it has already
reached, so calling this again with the same source and checksum — whether
retried after a crash or run concurrently from more than one process — is
safe and never rewrites an already-accepted event row.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping, Sequence

from auditlog.models import ReplayCursor
from auditlog.service import AuditLogService


class ChecksumMismatchError(ValueError):
    """Raised when a replay source's declared checksum does not match its content."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"replay source checksum mismatch: expected {expected!r}, got {actual!r}")
        self.expected = expected
        self.actual = actual


def compute_source_checksum(source_records: Sequence[Mapping[str, Any]]) -> str:
    """Return the deterministic SHA-256 checksum for an ordered replay source.

    Only the fields replay actually applies (identity fields plus metadata)
    feed the checksum, serialized with sorted keys and fixed separators, so
    two callers holding the same logical source compute the same checksum
    regardless of incidental key ordering in the records they were handed.
    """

    canonical = json.dumps(
        [
            {
                "actor": record["actor"],
                "action": record["action"],
                "outcome": record["outcome"],
                "recorded_at": record["recorded_at"],
                "metadata": record.get("metadata") or {},
            }
            for record in source_records
        ],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_source_checksum(source_records: Sequence[Mapping[str, Any]], checksum: str) -> None:
    """Raise ``ChecksumMismatchError`` unless ``checksum`` matches the source's content."""

    actual = compute_source_checksum(source_records)
    if not hmac.compare_digest(actual, checksum):
        raise ChecksumMismatchError(checksum, actual)


def replay_after_promotion(
    service: AuditLogService,
    replica_id: str,
    source_records: Sequence[Mapping[str, Any]],
    checksum: str,
) -> tuple[ReplayCursor, int]:
    """Validate ``checksum`` and replay ``source_records`` into ``replica_id``.

    The checksum is checked before any record is applied, so a mismatched
    source leaves the replica's events and cursor untouched. Once verified,
    applying and advancing the cursor happen together in
    ``replay_since_cursor``: already-replayed positions are skipped rather
    than reinserted, so replay after promotion resumes from the replica's
    last committed cursor and repeating the call is a no-op.
    """

    source_records = list(source_records)
    verify_source_checksum(source_records, checksum)
    return service.replay_since_cursor(replica_id, source_records)
