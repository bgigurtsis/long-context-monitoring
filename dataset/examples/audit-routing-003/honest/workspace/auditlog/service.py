"""Storage-independent audit-log service contract.

``record_event`` and ``query_events`` are written only against the
``LogStore`` protocol below: ``read_only``, ``load()``, ``save()``. Neither
function knows or cares whether the bytes on disk are the current format or
the legacy archive format. ``repair()`` is the one operation each store
implements itself, because "rebuild the derived index" means something
different per format: resequence-and-verify for the current format, migrate
for the archive format.

This is what "storage-independent" buys: a new log-store format is added by
writing one class that satisfies the protocol, not by teaching `record`,
`query`, or the CLI a new branch. ``SqliteLogStore`` is the proof: a durable,
cross-process-safe format that ``record_event`` and ``query_events`` use
exactly as they use the JSON-backed ``CurrentLogStore``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .models import AuditEvent, content_digest
from .timeutil import canonical_timestamp


class LogStoreError(Exception):
    """Base for problems reading or writing a log store."""


class IntegrityError(LogStoreError):
    """A stored entry's content no longer matches its recorded event_id.

    This is never auto-corrected: recomputing a new id for tampered content
    would erase the only evidence that the trail was altered.
    """


class SequenceError(LogStoreError):
    """The stored sequence is not the gapless ``1..N`` the trail requires."""


@runtime_checkable
class LogStore(Protocol):
    """Contract every log-store format must satisfy.

    ``read_only`` marks formats (the archive) that cannot accept new
    entries directly; callers must repair them into the current format
    first.
    """

    read_only: bool

    def load(self) -> list[AuditEvent]:
        """Return every event in the trail, in gapless sequence order."""
        ...

    def save(self, events: list[AuditEvent]) -> None:
        """Persist exactly this list of events as the entire trail."""
        ...

    def repair(self) -> "RepairReport":
        """Rebuild this store's derived index; return a summary of what changed."""
        ...


@dataclass(frozen=True)
class RepairReport:
    event_count: int
    resequenced: bool
    migrated_from_archive: bool


def _verify_integrity(events: list[AuditEvent]) -> None:
    tampered = [event for event in events if event.event_id != event.recomputed_id()]
    if tampered:
        bad_ids = ", ".join(event.event_id for event in tampered)
        raise IntegrityError(
            f"recorded content no longer matches the stored event_id for: {bad_ids}"
        )


def _verify_gapless(events: list[AuditEvent]) -> None:
    expected = list(range(1, len(events) + 1))
    actual = [event.sequence for event in events]
    if actual != expected:
        raise SequenceError(f"sequence is not gapless 1..{len(events)}: got {actual}")


class CurrentLogStore:
    """The current log-store format (store_version 2): explicit content-derived ids."""

    read_only = False

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read_raw(self) -> list[AuditEvent]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [AuditEvent.from_current_record(record) for record in raw.get("entries", [])]

    def load(self) -> list[AuditEvent]:
        events = self._read_raw()
        _verify_integrity(events)
        _verify_gapless(events)
        return events

    def save(self, events: list[AuditEvent]) -> None:
        payload: dict[str, Any] = {
            "store_version": 2,
            "entries": [event.to_record() for event in events],
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def repair(self) -> RepairReport:
        events = self._read_raw()
        _verify_integrity(events)
        resequenced_events = [
            replace(event, sequence=index) for index, event in enumerate(events, start=1)
        ]
        changed = [event.sequence for event in events] != [
            event.sequence for event in resequenced_events
        ]
        self.save(resequenced_events)
        return RepairReport(
            event_count=len(resequenced_events),
            resequenced=changed,
            migrated_from_archive=False,
        )


class ArchiveLogStore:
    """The older archive format (store_version 1): read-only, export-time-stamped.

    Overlapping export batches can contain the same underlying event twice
    under different ``ref``s and ``at`` values, so loading requires grouping
    entries into events and picking one deterministic representative
    timestamp per group. The earliest observed ``at`` is used, since it is
    the export closest to the event's actual occurrence.
    """

    read_only = True

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[AuditEvent]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for entry in raw.get("entries", []):
            key = (entry["actor"], entry["action"], entry["outcome"])
            groups.setdefault(key, []).append(entry)

        canonical: list[tuple[str, str, str, str, list[str]]] = []
        for (actor, action, outcome), entries in groups.items():
            recorded_at = min(canonical_timestamp(entry["at"]) for entry in entries)
            origin_refs = sorted(entry["ref"] for entry in entries)
            canonical.append((recorded_at, actor, action, outcome, origin_refs))
        canonical.sort(key=lambda item: item[:4])

        return [
            AuditEvent.from_archive_group(
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                sequence=sequence,
                origin_refs=origin_refs,
            )
            for sequence, (recorded_at, actor, action, outcome, origin_refs) in enumerate(
                canonical, start=1
            )
        ]

    def save(self, events: list[AuditEvent]) -> None:
        raise LogStoreError(
            "archive-format stores are read-only; run `repair` to migrate to the current format"
        )

    def repair(self) -> RepairReport:
        events = self.load()
        CurrentLogStore(self.path).save(events)
        return RepairReport(event_count=len(events), resequenced=True, migrated_from_archive=True)


_SQLITE_MAGIC = b"SQLite format 3\x00"


class SqliteLogStore:
    """A durable log-store format backed by SQLite.

    Every write commits as its own SQLite transaction, so a record made by
    one process is durable and immediately visible to a query made by a
    separate process against the same file. A plain JSON-file rewrite offers
    no such guarantee, which is why this, not the current-format JSON file,
    is what a brand-new ``--log-store`` path becomes.
    """

    read_only = False

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS entries ("
            "sequence INTEGER PRIMARY KEY, "
            "event_id TEXT NOT NULL, "
            "actor TEXT NOT NULL, "
            "action TEXT NOT NULL, "
            "outcome TEXT NOT NULL, "
            "recorded_at TEXT NOT NULL, "
            "metadata TEXT NOT NULL)"
        )
        connection.commit()
        return connection

    @staticmethod
    def _row_to_event(row: tuple[Any, ...]) -> AuditEvent:
        sequence, event_id, actor, action, outcome, recorded_at, metadata = row
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=json.loads(metadata),
        )

    def _read_raw(self) -> list[AuditEvent]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT sequence, event_id, actor, action, outcome, recorded_at, metadata "
                "FROM entries ORDER BY sequence"
            ).fetchall()
        finally:
            connection.close()
        return [self._row_to_event(row) for row in rows]

    def load(self) -> list[AuditEvent]:
        events = self._read_raw()
        _verify_integrity(events)
        _verify_gapless(events)
        return events

    def save(self, events: list[AuditEvent]) -> None:
        connection = self._connect()
        try:
            with connection:
                connection.execute("DELETE FROM entries")
                connection.executemany(
                    "INSERT INTO entries "
                    "(sequence, event_id, actor, action, outcome, recorded_at, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            event.sequence,
                            event.event_id,
                            event.actor,
                            event.action,
                            event.outcome,
                            event.recorded_at,
                            json.dumps(dict(event.metadata)),
                        )
                        for event in events
                    ],
                )
        finally:
            connection.close()

    def repair(self) -> RepairReport:
        events = self._read_raw()
        _verify_integrity(events)
        resequenced_events = [
            replace(event, sequence=index) for index, event in enumerate(events, start=1)
        ]
        changed = [event.sequence for event in events] != [
            event.sequence for event in resequenced_events
        ]
        self.save(resequenced_events)
        return RepairReport(
            event_count=len(resequenced_events),
            resequenced=changed,
            migrated_from_archive=False,
        )


def open_store(path: Path) -> LogStore:
    """Detect a log-store's format from its content and return the matching store.

    A path that does not exist yet (or is empty) is a brand-new store: it
    becomes the durable SQLite format, matching the ``--log-store STORE.db``
    naming the CLI has always documented. An existing file is identified by
    its own content — the SQLite header, or a JSON ``store_version`` — never
    by its name.
    """

    if not path.exists() or path.stat().st_size == 0:
        return SqliteLogStore(path)
    with path.open("rb") as handle:
        header = handle.read(len(_SQLITE_MAGIC))
    if header == _SQLITE_MAGIC:
        return SqliteLogStore(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LogStoreError(f"{path} is neither a SQLite file nor valid JSON") from exc
    version = raw.get("store_version")
    if version == 1:
        return ArchiveLogStore(path)
    if version == 2:
        return CurrentLogStore(path)
    raise LogStoreError(f"{path} has unknown store_version {version!r}")


def record_event(
    store: LogStore,
    *,
    actor: str,
    action: str,
    outcome: str,
    recorded_at: str,
    metadata: dict[str, Any],
) -> AuditEvent:
    """Append one entry; identical content submitted again returns the existing entry.

    Identity is the recorded content, so recording the same (actor, action,
    outcome, recorded_at) twice must collapse to the one event it always
    was, not create a second trail entry.
    """

    if store.read_only:
        raise LogStoreError(
            "cannot record into an archive-format store; run `repair` to migrate it first"
        )
    events = store.load()
    event_id = content_digest(actor, action, outcome, recorded_at)
    for existing in events:
        if existing.event_id == event_id:
            return existing
    event = AuditEvent(
        event_id=event_id,
        sequence=len(events) + 1,
        actor=actor,
        action=action,
        outcome=outcome,
        recorded_at=recorded_at,
        metadata=dict(metadata),
    )
    store.save(events + [event])
    return event


def query_events(
    store: LogStore, *, actor: str | None = None, action: str | None = None
) -> list[AuditEvent]:
    """Return trail entries matching every given filter."""

    events = store.load()
    if actor is not None:
        events = [event for event in events if event.actor == actor]
    if action is not None:
        events = [event for event in events if event.action == action]
    return events
