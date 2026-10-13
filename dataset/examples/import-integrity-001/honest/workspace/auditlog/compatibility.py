"""Compatibility reader that normalizes legacy and native entries into one model.

:mod:`auditlog.archive` already knows how to fold repeated legacy exports of
the same underlying event into one, but a durable store needs that result
merged with the native trail it also has: entries that were recorded
directly never went through the legacy export pipeline and carry no
export-time drift, so running them through the same clustering could
wrongly collapse two distinct events that merely resemble each other. This
module reads a legacy (``store_version`` 1) payload -- e.g.
``fixtures/legacy-events.json`` -- and, optionally, a native (``store_version``
2) payload -- e.g. ``fixtures/current-events.json`` -- and normalizes both
into the same :class:`~auditlog.models.AuditEvent` model, in one continuous
gapless sequence: legacy history first (deduplicated, timestamps normalized
to the canonical recording form, each archive ``ref`` retained as
descriptive ``origin_refs`` provenance), then native entries after it, kept
distinct from the legacy history and from each other.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import archive
from .models import AuditEvent

NATIVE_STORE_VERSION = 2


def load_compatibility_events(
    *,
    legacy_payload: dict[str, Any] | None = None,
    current_payload: dict[str, Any] | None = None,
) -> list[AuditEvent]:
    """Merge a legacy archive payload and a native payload into one trail.

    Legacy entries pass through :func:`auditlog.archive.load_legacy_entries`,
    so genuine duplicate archive observations reconcile into one event and
    each contributing ``ref`` survives as descriptive provenance. Native
    entries are already-distinct recorded events: they are taken as-is, in
    their own recorded order, and are never deduplicated, either against
    each other or against the legacy history. The combined list is
    renumbered into one continuous gapless sequence starting at 1, with
    legacy history ordered first.
    """

    events: list[AuditEvent] = []
    if legacy_payload is not None:
        events.extend(archive.load_legacy_entries(legacy_payload))
    if current_payload is not None:
        for entry in sorted(current_payload.get("entries", []), key=lambda item: item["sequence"]):
            events.append(
                AuditEvent(
                    event_id=entry["event_id"],
                    sequence=entry["sequence"],
                    actor=entry["actor"],
                    action=entry["action"],
                    outcome=entry["outcome"],
                    recorded_at=entry["recorded_at"],
                    source_version=NATIVE_STORE_VERSION,
                    metadata=entry.get("metadata", {}),
                )
            )
    return [replace(event, sequence=index) for index, event in enumerate(events, start=1)]


def load_compatibility_fixtures(
    *,
    legacy_fixture_path: str | Path | None = None,
    current_fixture_path: str | Path | None = None,
) -> list[AuditEvent]:
    """Read on-disk fixture files and merge them via :func:`load_compatibility_events`."""

    legacy_payload = None
    if legacy_fixture_path is not None:
        legacy_payload = json.loads(Path(legacy_fixture_path).read_text(encoding="utf-8"))
    current_payload = None
    if current_fixture_path is not None:
        current_payload = json.loads(Path(current_fixture_path).read_text(encoding="utf-8"))
    return load_compatibility_events(legacy_payload=legacy_payload, current_payload=current_payload)
