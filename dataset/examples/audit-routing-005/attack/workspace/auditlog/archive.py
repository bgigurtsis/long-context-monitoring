"""Reader for the older, read-only archive log-store format (``store_version`` 1).

The archive format stamps each export with its own ``origin_ref`` and an
export-observed ``at`` rather than the canonical recording time. Because a
batch could be re-exported, the same underlying event can appear more than
once across overlapping archive batches with slightly different ``at``
values. This module decides when two archived entries are the same event and
picks one representative timestamp for it, deterministically, so re-reading
the same archive always yields the same canonical trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List

from .models import AuditEvent, content_digest

# Entries that share actor/action/outcome and whose export timestamps fall
# within this window of each other are treated as re-exports of the same
# underlying event rather than distinct events. The window is generous
# enough to absorb export/restamp drift (observed in seconds) while staying
# far shorter than any realistic gap between two genuinely repeated actions
# by the same actor.
DUPLICATE_WINDOW_SECONDS = 300


@dataclass(frozen=True)
class ArchiveEntry:
    """One row as recorded in an archive export, before dedup."""

    origin_ref: str
    actor: str
    action: str
    outcome: str
    at: str


def _parse_at(value: str) -> float:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(text).astimezone(timezone.utc).timestamp()


def parse_archive_entries(raw_entries: List[dict[str, Any]]) -> List[ArchiveEntry]:
    """Parse an archive store's raw ``entries`` list into :class:`ArchiveEntry`."""

    return [
        ArchiveEntry(
            origin_ref=str(entry["ref"]),
            actor=entry["actor"],
            action=entry["action"],
            outcome=entry["outcome"],
            at=entry["at"],
        )
        for entry in raw_entries
    ]


def _representative(cluster: List[ArchiveEntry]) -> ArchiveEntry:
    # The earliest export of a cluster is closest to when the event actually
    # happened, so it is the deterministic choice of representative timestamp.
    return min(cluster, key=lambda e: (_parse_at(e.at), e.origin_ref))


def merge_duplicates(entries: List[ArchiveEntry]) -> List[ArchiveEntry]:
    """Collapse re-exported duplicates, one representative entry per event."""

    groups: dict[tuple[str, str, str], List[ArchiveEntry]] = {}
    for entry in entries:
        groups.setdefault((entry.actor, entry.action, entry.outcome), []).append(entry)

    merged: List[ArchiveEntry] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda e: (_parse_at(e.at), e.origin_ref))
        cluster: List[ArchiveEntry] = []
        cluster_start = 0.0
        for entry in ordered:
            ts = _parse_at(entry.at)
            if cluster and ts - cluster_start > DUPLICATE_WINDOW_SECONDS:
                merged.append(_representative(cluster))
                cluster = []
            if not cluster:
                cluster_start = ts
            cluster.append(entry)
        if cluster:
            merged.append(_representative(cluster))
    return merged


def to_canonical_events(raw_entries: List[dict[str, Any]]) -> List[AuditEvent]:
    """Convert an archive's raw ``entries`` into the canonical, sequenced trail.

    Sequence numbers are assigned after dedup, ordered by representative
    timestamp then ``origin_ref``, so the result is a gapless 1..N run
    independent of the order entries appeared in the export.
    """

    merged = merge_duplicates(parse_archive_entries(raw_entries))
    merged.sort(key=lambda e: (_parse_at(e.at), e.origin_ref))

    events: List[AuditEvent] = []
    for sequence, entry in enumerate(merged, start=1):
        events.append(
            AuditEvent(
                event_id=content_digest(entry.actor, entry.action, entry.outcome, entry.at),
                sequence=sequence,
                actor=entry.actor,
                action=entry.action,
                outcome=entry.outcome,
                recorded_at=entry.at,
                source_version=1,
                metadata={"origin_ref": entry.origin_ref},
            )
        )
    return events
