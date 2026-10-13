"""Reader for the legacy (``store_version`` 1) archive format.

The archive format stamped each entry with an export-observed ``at`` rather
than the canonical recording time, and could re-export the same underlying
event with a different ``at`` on each pass. Reading it therefore requires a
deterministic rule for when two archived entries are the same event and,
once merged, which timestamp represents it.

The rule used here: entries that share ``actor``, ``action`` and ``outcome``
and whose ``at`` values fall within ``DEDUPE_WINDOW`` of each other are the
same event exported more than once. Chained gaps (A close to B, B close to
C) merge transitively. The representative timestamp is the earliest ``at``
in the cluster, since later ones are later re-exports drifting forward from
the original recording, never before it. Distinct events are then ordered by
that representative timestamp to assign gapless sequence numbers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .models import AuditEvent, content_digest

DEDUPE_WINDOW = timedelta(seconds=5)


class ArchiveFormatError(ValueError):
    """Raised when an archive entry is missing a required field or is malformed."""


def _parse_at(raw: str) -> datetime:
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ArchiveFormatError(f"unparsable archive timestamp {raw!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_recorded_at(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_legacy_entries(payload: dict[str, Any]) -> list[AuditEvent]:
    """Parse a ``store_version`` 1 payload into deduplicated, validated events."""

    raw_entries = payload.get("entries", [])
    parsed = []
    for raw in raw_entries:
        try:
            actor = raw["actor"]
            action = raw["action"]
            outcome = raw["outcome"]
            ref = raw["ref"]
            at = _parse_at(raw["at"])
        except KeyError as exc:
            raise ArchiveFormatError(f"archive entry missing field {exc.args[0]!r}") from exc
        parsed.append((actor, action, outcome, at, ref))

    clusters: list[dict[str, Any]] = []
    for actor, action, outcome, at, ref in sorted(parsed, key=lambda item: item[3]):
        merged = False
        for cluster in clusters:
            if (
                cluster["actor"] == actor
                and cluster["action"] == action
                and cluster["outcome"] == outcome
                and at - cluster["latest_at"] <= DEDUPE_WINDOW
            ):
                cluster["latest_at"] = at
                cluster["earliest_at"] = min(cluster["earliest_at"], at)
                cluster["refs"].append(ref)
                merged = True
                break
        if not merged:
            clusters.append(
                {
                    "actor": actor,
                    "action": action,
                    "outcome": outcome,
                    "earliest_at": at,
                    "latest_at": at,
                    "refs": [ref],
                }
            )

    clusters.sort(key=lambda cluster: cluster["earliest_at"])

    events = []
    for sequence, cluster in enumerate(clusters, start=1):
        recorded_at = _canonical_recorded_at(cluster["earliest_at"])
        event_id = content_digest(cluster["actor"], cluster["action"], cluster["outcome"], recorded_at)
        events.append(
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=cluster["actor"],
                action=cluster["action"],
                outcome=cluster["outcome"],
                recorded_at=recorded_at,
                source_version=1,
                metadata={"origin_refs": sorted(cluster["refs"])},
            )
        )
    return events
