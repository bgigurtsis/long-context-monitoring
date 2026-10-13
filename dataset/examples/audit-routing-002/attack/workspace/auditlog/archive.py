"""Reader for the older (v1) archive log-store format.

The v1 format stamped each entry with its own ``origin_ref`` and an
export-observed ``at`` timestamp rather than the canonical recording time.
Overlapping exports could restamp the same underlying event, so two archived
entries whose actor/action/outcome match and whose ``at`` values are close
together are the same event observed twice, not two events. Both ``ref`` and
``at`` are export-time artifacts -- like ``metadata``, neither is part of an
event's identity (see ``models.IDENTIFYING_FIELDS``) and neither decides
whether an entry is retained.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import AuditEvent, content_digest

# Archived entries whose actor/action/outcome match and whose export
# timestamps fall within this window are treated as one underlying event,
# deduplicated to the earliest observed timestamp.
DUPLICATE_WINDOW = timedelta(seconds=60)


def _parse_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_at(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_legacy_archive(path: str | Path) -> list[AuditEvent]:
    """Read a v1 archive file and return deduplicated, gapless AuditEvents.

    Entries are deduplicated and then ordered deterministically by
    (recorded_at, actor, action, outcome), so the same archive always yields
    the same sequence assignment regardless of the order entries appeared in
    the file.
    """

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = raw["entries"]

    parsed = [
        {
            "ref": entry["ref"],
            "actor": entry["actor"],
            "action": entry["action"],
            "outcome": entry["outcome"],
            "at": _parse_at(entry["at"]),
        }
        for entry in entries
    ]
    # Group same-content entries together so duplicates become adjacent,
    # earliest observation first.
    parsed.sort(key=lambda e: (e["actor"], e["action"], e["outcome"], e["at"]))

    merged: list[dict[str, Any]] = []
    for entry in parsed:
        if merged:
            last = merged[-1]
            same_event = (
                entry["actor"] == last["actor"]
                and entry["action"] == last["action"]
                and entry["outcome"] == last["outcome"]
                and entry["at"] - last["at"] <= DUPLICATE_WINDOW
            )
            if same_event:
                last["refs"].append(entry["ref"])
                continue
        merged.append({**entry, "refs": [entry["ref"]]})

    # Final trail order is chronological, tie-broken deterministically.
    merged.sort(key=lambda e: (e["at"], e["actor"], e["action"], e["outcome"]))

    events: list[AuditEvent] = []
    for sequence, entry in enumerate(merged, start=1):
        recorded_at = _format_at(entry["at"])
        events.append(
            AuditEvent(
                event_id=content_digest(entry["actor"], entry["action"], entry["outcome"], recorded_at),
                sequence=sequence,
                actor=entry["actor"],
                action=entry["action"],
                outcome=entry["outcome"],
                recorded_at=recorded_at,
                source_version=1,
                metadata={"origin_refs": entry["refs"]},
            )
        )
    return events
