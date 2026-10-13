"""Compatibility reader: normalizes legacy and current log-store documents into one model.

Two archive shapes exist. The current shape (``store_version`` 2) records
each entry with its own content-derived ``event_id`` and an explicit gapless
``sequence``: every entry is read back exactly once, verbatim, because two
native entries that happen to share an actor/action/outcome are still two
distinct recorded facts, not a duplicate observation of one fact.

The legacy archive shape (``store_version`` 1) instead recorded each entry
under an export batch's own ``ref`` and an export-observed ``at`` timestamp.
Because the same underlying event could be exported more than once with a
few seconds of drift between ``at`` values, reading this shape requires
reconciling genuine duplicate *observations* of one event into a single
entry — unlike the current shape, where every entry is already exactly one
event and is never a duplicate observation of another.

Both readers return the same domain type, ``AuditEvent``, so a caller never
needs to know in advance which shape a document was read from to work with
what it produced. ``source_version`` on the resulting entry keeps that
provenance without leaking it into the entry's identity, and
``normalize_archive`` dispatches to the right reader from the document's own
``store_version`` field.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .errors import StorageCorruptionError
from .models import AuditEvent, CURRENT_SOURCE_VERSION, load_event, new_event, validate_sequence

LEGACY_SOURCE_VERSION = 1
_DUPLICATE_WINDOW = timedelta(seconds=30)


def _parse_legacy_at(raw: str) -> datetime:
    body = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(body)
    except ValueError as exc:
        raise StorageCorruptionError(f"legacy entry has an unparseable 'at' value {raw!r}") from exc


def read_legacy_archive(doc: dict[str, Any]) -> list[AuditEvent]:
    """Convert a store_version-1 archive document into deduplicated entries.

    Entries that share actor/action/outcome and fall within
    ``_DUPLICATE_WINDOW`` of each other are treated as export-time drift on
    one underlying event: they collapse to a single entry, using the
    earliest ``at`` as the canonical, timestamp-normalized ``recorded_at``
    and retaining every contributing ``ref`` as descriptive provenance in
    ``metadata["origin_refs"]``.
    """

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for raw in doc.get("entries", []):
        try:
            key = (raw["actor"], raw["action"], raw["outcome"])
        except KeyError as exc:
            raise StorageCorruptionError(f"legacy entry is missing required field {exc}") from exc
        groups.setdefault(key, []).append(raw)

    clusters: list[list[dict[str, Any]]] = []
    for raws in groups.values():
        ordered = sorted(raws, key=lambda r: _parse_legacy_at(r["at"]))
        group_clusters: list[list[dict[str, Any]]] = []
        for raw in ordered:
            if group_clusters and (
                _parse_legacy_at(raw["at"]) - _parse_legacy_at(group_clusters[-1][-1]["at"])
                <= _DUPLICATE_WINDOW
            ):
                group_clusters[-1].append(raw)
            else:
                group_clusters.append([raw])
        clusters.extend(group_clusters)

    def cluster_sort_key(cluster: list[dict[str, Any]]) -> tuple[datetime, str, str]:
        earliest = min(cluster, key=lambda r: _parse_legacy_at(r["at"]))
        return (_parse_legacy_at(earliest["at"]), earliest["actor"], earliest["action"])

    clusters.sort(key=cluster_sort_key)

    events: list[AuditEvent] = []
    for sequence, cluster in enumerate(clusters, start=1):
        chosen = min(cluster, key=lambda r: _parse_legacy_at(r["at"]))
        recorded_at = _parse_legacy_at(chosen["at"]).strftime("%Y-%m-%dT%H:%M:%SZ")
        refs = sorted(r["ref"] for r in cluster if "ref" in r)
        built = new_event(
            chosen["actor"],
            chosen["action"],
            chosen["outcome"],
            recorded_at,
            sequence,
            metadata={"origin_refs": refs},
        )
        events.append(
            AuditEvent(
                event_id=built.event_id,
                sequence=built.sequence,
                actor=built.actor,
                action=built.action,
                outcome=built.outcome,
                recorded_at=built.recorded_at,
                source_version=LEGACY_SOURCE_VERSION,
                metadata=built.metadata,
            )
        )
    return events


def read_current_archive(doc: dict[str, Any]) -> list[AuditEvent]:
    """Read a store_version-2 document's entries verbatim, one event each.

    Every entry here already carries its own recorded content and derived
    id, so unlike the legacy reader, entries are never clustered or merged:
    a native entry that shares actor/action/outcome with another stays a
    distinct entry.
    """

    events: list[AuditEvent] = []
    previous_sequence = 0
    for raw in doc.get("entries", []):
        event = load_event(raw)
        validate_sequence(previous_sequence, event.sequence)
        previous_sequence = event.sequence
        events.append(event)
    return events


def normalize_archive(doc: dict[str, Any]) -> list[AuditEvent]:
    """Normalize either archive shape into the same ``AuditEvent`` model.

    Dispatches purely on the document's own ``store_version``, so a caller
    never needs to know in advance which shape it is handing in.
    """

    version = doc.get("store_version")
    if version == LEGACY_SOURCE_VERSION:
        return read_legacy_archive(doc)
    if version == CURRENT_SOURCE_VERSION:
        return read_current_archive(doc)
    raise StorageCorruptionError(f"unsupported store_version {version!r}")
