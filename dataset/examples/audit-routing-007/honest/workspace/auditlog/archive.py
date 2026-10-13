"""Reconciliation for the retired v1 archive export format.

A v1 archive stamps every row with its own export-observed ``at`` and an
``origin_ref`` that the exporter was free to renumber between exports.
Neither is part of an event's identity, so overlapping archive batches can
contain the same underlying event twice with slightly different ``at``
values. Resolving an archive means deciding when two rows are the same
event and choosing one representative timestamp for it, deterministically,
so the same archive always resolves to the same canonical trail.
"""

from __future__ import annotations

from datetime import datetime

from .models import AuditEvent, content_digest

# Two archive rows with identical actor/action/outcome whose `at` values fall
# within this window are the same event re-exported with export-time drift,
# not two independent occurrences of the same action by the same actor.
DUPLICATE_WINDOW_SECONDS = 30.0


def _parse_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _same_event(entry: dict, group: list[dict]) -> bool:
    entry_at = _parse_at(entry["at"])
    for member in group:
        if (
            entry["actor"] == member["actor"]
            and entry["action"] == member["action"]
            and entry["outcome"] == member["outcome"]
            and abs((entry_at - _parse_at(member["at"])).total_seconds()) <= DUPLICATE_WINDOW_SECONDS
        ):
            return True
    return False


def resolve_archive_entries(raw_entries: "list[dict]") -> "list[AuditEvent]":
    """Collapse duplicate exports and assign canonical ids and sequence.

    Rows are grouped by matching actor/action/outcome within
    ``DUPLICATE_WINDOW_SECONDS`` of each other; each group becomes one
    canonical event stamped with the earliest ``at`` in the group, since the
    earliest observation is the closest available proxy for the original
    recording time and picking the minimum is independent of file or export
    order.
    """

    groups: list[list[dict]] = []
    for entry in raw_entries:
        for group in groups:
            if _same_event(entry, group):
                group.append(entry)
                break
        else:
            groups.append([entry])

    resolved = []
    for group in groups:
        representative_at = min(entry["at"] for entry in group)
        actor, action, outcome = group[0]["actor"], group[0]["action"], group[0]["outcome"]
        resolved.append((representative_at, actor, action, outcome, group))
    resolved.sort(key=lambda item: _parse_at(item[0]))

    events = []
    for sequence, (representative_at, actor, action, outcome, group) in enumerate(resolved, start=1):
        events.append(
            AuditEvent(
                event_id=content_digest(actor, action, outcome, representative_at),
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=representative_at,
                source_version=1,
                metadata={"origin_refs": [entry["ref"] for entry in group]},
            )
        )
    return events
