"""Reader for the older, pre-v2 archive log-store format.

The archive format restamped an entry's export-observed ``at`` value and
could renumber its ``ref`` between exports, so the same underlying event can
appear more than once across overlapping archive batches. Neither ``ref``
nor ``at`` is reliable on its own; merging decides which archived entries are
the same event and picks one representative timestamp deterministically, so
re-reading the same archive always yields the same canonical trail.
"""

from __future__ import annotations

from datetime import datetime

from .models import AuditEvent, content_digest

# actor/action/outcome are the only fields every restamp/renumber left
# untouched, so together they identify the underlying event.
_DUPLICATE_KEY_FIELDS = ("actor", "action", "outcome")


def merge_legacy_entries(raw_entries: list[dict]) -> list[AuditEvent]:
    """Collapse duplicate archive entries into canonical events.

    Entries sharing actor/action/outcome are the same event recorded more
    than once across export batches. The earliest ``at`` becomes the
    canonical ``recorded_at``, and every origin ``ref`` that pointed at the
    event is kept in ``metadata`` for traceability. The result is numbered
    with a gapless sequence in first-seen order.
    """

    buckets: dict[tuple[str, str, str], dict] = {}
    order: list[tuple[str, str, str]] = []
    for raw in raw_entries:
        key = (raw["actor"], raw["action"], raw["outcome"])
        if key not in buckets:
            buckets[key] = {"at": raw["at"], "refs": [raw["ref"]]}
            order.append(key)
            continue
        bucket = buckets[key]
        bucket["refs"].append(raw["ref"])
        if _parse_at(raw["at"]) < _parse_at(bucket["at"]):
            bucket["at"] = raw["at"]

    events = []
    for sequence, key in enumerate(order, start=1):
        actor, action, outcome = key
        bucket = buckets[key]
        recorded_at = bucket["at"]
        events.append(
            AuditEvent(
                event_id=content_digest(actor, action, outcome, recorded_at),
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=1,
                metadata={"origin_refs": bucket["refs"]},
            )
        )
    return events


def _parse_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
