"""The append-only log store: persistence, querying, and repair.

A log store is a single JSON file under the configured storage root (see
``resolve_store_path``). The current format mirrors ``AuditEvent`` directly;
the legacy archive format (``store_version`` 1) is read and migrated by
``repair`` via :func:`_migrate_legacy_entries`.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AuditEvent, content_digest

CURRENT_STORE_VERSION = 2
LEGACY_STORE_VERSION = 1

# Overrides where log stores may live; unset means "the current directory".
STORAGE_ROOT_ENV = "AUDITLOG_STORAGE_ROOT"

# Archive entries for the same actor/action/outcome whose export-observed
# ``at`` values fall within this many seconds of each other are treated as
# one underlying event exported twice by overlapping archive batches, rather
# than two real occurrences of the same kind of event.
ARCHIVE_DEDUPE_WINDOW_SECONDS = 5


class LogStoreError(Exception):
    """Raised for invalid or unsafe log-store operations."""


@dataclass(frozen=True)
class RepairReport:
    """Outcome of a ``repair`` run."""

    migrated_from_version: int
    entry_count: int
    tampered_event_ids: list[str]


def storage_root() -> Path:
    """The directory all log stores must resolve under."""

    raw = os.environ.get(STORAGE_ROOT_ENV)
    return (Path(raw) if raw else Path.cwd()).resolve()


def resolve_store_path(raw_path: str | os.PathLike[str], root: Path | None = None) -> Path:
    """Resolve a caller-supplied log-store path to a location under ``root``.

    Rejects any path -- absolute, or containing ``..`` -- that would resolve
    outside the storage root, so a caller cannot make the service read or
    write files elsewhere on the machine.
    """

    root = (root or storage_root()).resolve()
    candidate = Path(raw_path)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise LogStoreError(
            f"log store path {str(raw_path)!r} resolves outside the storage root {root}"
        ) from None
    return resolved


def now_recorded_at() -> str:
    """The canonical recording time for an entry created right now."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _migrate_legacy_entries(raw_entries: list[dict[str, Any]]) -> list[AuditEvent]:
    """Convert store-version-1 archive entries into canonical events.

    Overlapping archive exports can carry the same underlying event twice
    with slightly different ``at`` values, so entries that share an
    actor/action/outcome and fall within the dedupe window of each other are
    collapsed into one event. The earliest ``at`` in the group becomes the
    canonical ``recorded_at``, since it is closest to when the event actually
    happened; the group's archive refs are kept as descriptive metadata.
    """

    parsed = [
        {
            "ref": raw["ref"],
            "actor": raw["actor"],
            "action": raw["action"],
            "outcome": raw["outcome"],
            "at_dt": _parse_timestamp(raw["at"]),
        }
        for raw in raw_entries
    ]

    groups: list[list[dict[str, Any]]] = []
    for item in parsed:
        for group in groups:
            representative = group[0]
            same_event = (
                representative["actor"] == item["actor"]
                and representative["action"] == item["action"]
                and representative["outcome"] == item["outcome"]
                and abs((representative["at_dt"] - item["at_dt"]).total_seconds())
                <= ARCHIVE_DEDUPE_WINDOW_SECONDS
            )
            if same_event:
                group.append(item)
                break
        else:
            groups.append([item])

    # Chronological order, independent of how the archive happened to list entries.
    groups.sort(key=lambda group: min(item["at_dt"] for item in group))

    events = []
    for index, group in enumerate(groups, start=1):
        earliest = min(group, key=lambda item: item["at_dt"])
        recorded_at = earliest["at_dt"].strftime("%Y-%m-%dT%H:%M:%SZ")
        event_id = content_digest(
            earliest["actor"], earliest["action"], earliest["outcome"], recorded_at
        )
        origin_refs = sorted(item["ref"] for item in group)
        events.append(
            AuditEvent(
                event_id=event_id,
                sequence=index,
                actor=earliest["actor"],
                action=earliest["action"],
                outcome=earliest["outcome"],
                recorded_at=recorded_at,
                metadata={"origin_refs": origin_refs},
            )
        )
    return events


class AuditLogStore:
    """Append-only audit trail backed by a single JSON file."""

    def __init__(self, path: str | os.PathLike[str], root: Path | None = None) -> None:
        self.path = resolve_store_path(path, root)
        self._lock = threading.Lock()

    def _read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"store_version": CURRENT_STORE_VERSION, "entries": []}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_raw(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, self.path)

    def _load_events(self) -> tuple[int, list[AuditEvent]]:
        raw = self._read_raw()
        version = raw.get("store_version", CURRENT_STORE_VERSION)
        if version == LEGACY_STORE_VERSION:
            return version, _migrate_legacy_entries(raw.get("entries", []))
        if version != CURRENT_STORE_VERSION:
            raise LogStoreError(f"unsupported log store version: {version!r}")
        events = [
            AuditEvent(
                event_id=entry["event_id"],
                sequence=entry["sequence"],
                actor=entry["actor"],
                action=entry["action"],
                outcome=entry["outcome"],
                recorded_at=entry["recorded_at"],
                metadata=entry.get("metadata", {}),
            )
            for entry in raw.get("entries", [])
        ]
        return version, events

    def _save_events(self, events: list[AuditEvent]) -> None:
        payload = {
            "store_version": CURRENT_STORE_VERSION,
            "entries": [
                {
                    "event_id": event.event_id,
                    "sequence": event.sequence,
                    "actor": event.actor,
                    "action": event.action,
                    "outcome": event.outcome,
                    "recorded_at": event.recorded_at,
                    "metadata": event.metadata,
                }
                for event in events
            ],
        }
        self._write_raw(payload)

    def record(
        self, actor: str, action: str, outcome: str, metadata: dict[str, str] | None = None
    ) -> AuditEvent:
        """Append a new entry, stamped with the current time, and persist it."""

        with self._lock:
            _, events = self._load_events()
            recorded_at = now_recorded_at()
            event_id = content_digest(actor, action, outcome, recorded_at)
            entry = AuditEvent(
                event_id=event_id,
                sequence=len(events) + 1,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                metadata=dict(metadata or {}),
            )
            events.append(entry)
            self._save_events(events)
            return entry

    def query(self, actor: str | None = None, action: str | None = None) -> list[AuditEvent]:
        with self._lock:
            _, events = self._load_events()
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def repair(self) -> RepairReport:
        """Rebuild the gapless sequence, migrating an archive store in place.

        A mismatch between a stored ``event_id`` and its recomputed digest
        means the entry's content was edited after the fact. Repair reports
        that tampering rather than silently overwriting the id, since doing
        so would erase the only evidence that the content changed.
        """

        with self._lock:
            version, events = self._load_events()
            ordered = sorted(events, key=lambda event: event.sequence)
            tampered_ids = [
                event.event_id for event in ordered if event.event_id != event.recomputed_id()
            ]
            rebuilt = [
                AuditEvent(
                    event_id=event.event_id,
                    sequence=index,
                    actor=event.actor,
                    action=event.action,
                    outcome=event.outcome,
                    recorded_at=event.recorded_at,
                    metadata=event.metadata,
                )
                for index, event in enumerate(ordered, start=1)
            ]
            self._save_events(rebuilt)
            return RepairReport(
                migrated_from_version=version,
                entry_count=len(rebuilt),
                tampered_event_ids=tampered_ids,
            )
