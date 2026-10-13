"""Normalizes the legacy (`store_version` 1) archive format.

The archive format re-exports events with its own `ref` and an
export-observed `at`, not the canonical recording time. The same
underlying event can appear more than once across overlapping export
batches with a slightly different `at` each time -- see
fixtures/legacy-events.json, where the first two entries are the same
policy.update event re-exported two seconds apart. Duplicates never share
a `ref`, so `ref` cannot be the dedupe key, and `metadata` is
caller-supplied context, never identity (see
`auditlog.models.IDENTIFYING_FIELDS`). Content plus proximity in time is
the only signal available, so entries sharing (actor, action, outcome)
within `DEDUPE_WINDOW` of each other are folded into one event.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from auditlog.models import content_digest

# Two exports of the same event land close together; two independent
# occurrences of the same actor/action/outcome do not. Chosen generously
# above the 2-second drift in the seed fixture and well below any
# realistic gap between unrelated occurrences of the same action.
DEDUPE_WINDOW = timedelta(minutes=5)


def _parse_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_legacy_entries(raw_entries: list[dict]) -> list[dict]:
    """Collapse export duplicates and return canonical current-shape entries.

    Entries are grouped by (actor, action, outcome), then split into
    clusters wherever consecutive `at` values (sorted ascending) are more
    than `DEDUPE_WINDOW` apart; each cluster is one underlying event. The
    representative `recorded_at` is the earliest `at` in its cluster --
    the export closest to the true recording time -- so the result does
    not depend on the order entries were read in or how export batches
    happened to overlap.
    """

    groups: dict[tuple[str, str, str], list[dict]] = {}
    for raw in raw_entries:
        key = (raw["actor"], raw["action"], raw["outcome"])
        groups.setdefault(key, []).append(raw)

    events: list[dict] = []
    for (actor, action, outcome), members in groups.items():
        ordered = sorted(members, key=lambda member: _parse_at(member["at"]))
        cluster: list[dict] = []
        for member in ordered:
            if cluster and _parse_at(member["at"]) - _parse_at(cluster[-1]["at"]) > DEDUPE_WINDOW:
                events.append(_build_event(actor, action, outcome, cluster))
                cluster = []
            cluster.append(member)
        if cluster:
            events.append(_build_event(actor, action, outcome, cluster))

    events.sort(key=lambda event: event["recorded_at"])
    return events


def _build_event(actor: str, action: str, outcome: str, cluster: list[dict]) -> dict:
    recorded_at = min(member["at"] for member in cluster)
    return {
        "event_id": content_digest(actor, action, outcome, recorded_at),
        "actor": actor,
        "action": action,
        "outcome": outcome,
        "recorded_at": recorded_at,
        "source_version": 1,
        "metadata": {"origin_refs": [member["ref"] for member in cluster]},
    }
