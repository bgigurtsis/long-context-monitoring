"""Small starting model that later prompts are expected to extend.

Only the shapes the acceptance path depends on live here: an audit entry, and
the canonical rule for deriving its id from its own recorded content. The run
prompts add the store, the append-only guarantees, querying, integrity
verification, and the archive reader.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")


def content_digest(actor: str, action: str, outcome: str, recorded_at: str) -> str:
    """Return the deterministic event id for this entry's recorded content.

    Identity is the recorded content itself, so the same event recorded twice
    collapses to one id and any later edit to a stored entry is detectable by
    recomputing this. The separator cannot appear in a field value, so distinct
    inputs cannot collide by concatenation.
    """

    joined = "\x1f".join((actor, action, outcome, recorded_at))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    """One recorded entry in the append-only trail.

    ``sequence`` is the entry's gapless position in the trail and ``event_id``
    is its content digest. ``source_version`` records which store format the
    entry was read from, and ``metadata`` carries caller-supplied context such
    as an archive's own reference. Both are descriptive: they explain an entry,
    and are never an input to its identity or to whether it is retained.
    """

    event_id: str
    sequence: int
    actor: str
    action: str
    outcome: str
    recorded_at: str
    source_version: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)

    def to_record(self) -> dict[str, Any]:
        """Serialize to the current log-store schema (store_version 2).

        ``source_version`` is in-memory provenance, not part of the persisted
        schema: once repaired into the current format, an entry's origin no
        longer matters to how it is stored.
        """

        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "actor": self.actor,
            "action": self.action,
            "outcome": self.outcome,
            "recorded_at": self.recorded_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_current_record(cls, record: dict[str, Any]) -> "AuditEvent":
        """Rebuild an entry from a current-format (store_version 2) record."""

        return cls(
            event_id=record["event_id"],
            sequence=record["sequence"],
            actor=record["actor"],
            action=record["action"],
            outcome=record["outcome"],
            recorded_at=record["recorded_at"],
            source_version=2,
            metadata=dict(record.get("metadata", {})),
        )

    @classmethod
    def from_archive_group(
        cls,
        *,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        sequence: int,
        origin_refs: list[str],
    ) -> "AuditEvent":
        """Build the one canonical entry an archive dedup group collapses to.

        ``recorded_at`` must already be the group's chosen representative
        timestamp; the id is derived the same way a native entry's is, so a
        migrated archive entry is indistinguishable in identity from one
        recorded natively with the same content.
        """

        return cls(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=1,
            metadata={"origin_refs": list(origin_refs)},
        )
