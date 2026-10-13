"""Storage adapters for the audit log service.

``AuditService`` (see :mod:`auditlog.service`) only ever sees canonical,
immutable ``AuditEvent`` objects. Everything format-specific -- current vs.
archive log-store shape, JSON on disk vs. a plain Python list -- lives here,
behind the small :class:`LogStore` seam. That is what makes the service
storage-independent: swap the adapter and nothing above this module changes.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from auditlog.models import AuditEvent, LegacyRecord, reconcile_legacy_records


@dataclass(frozen=True)
class StoreState:
    """Canonical events read back from a store, plus the format they came from.

    ``source_version`` is 2 for a store already in current form (including an
    empty, not-yet-created one) and 1 when the events were reconciled out of
    the older archive format. The service uses it to decide whether ``repair``
    needs to migrate the store to current form.
    """

    events: tuple[AuditEvent, ...]
    source_version: int


class LogStore(Protocol):
    """The only surface ``AuditService`` is written against."""

    def read_state(self) -> StoreState:
        ...

    def write_events(self, events: tuple[AuditEvent, ...]) -> None:
        ...

    def read_index(self) -> dict | None:
        ...

    def write_index(self, index: dict) -> None:
        ...


class InMemoryLogStore:
    """Reference ``LogStore`` backed by a plain list.

    Exists so tests can prove the service has no dependency on any particular
    persistence format: the same ``AuditService`` behavior is exercised here
    and against :class:`JsonFileLogStore`.
    """

    def __init__(self, events: tuple[AuditEvent, ...] = (), source_version: int = 2) -> None:
        self._events = events
        self._source_version = source_version
        self._index: dict | None = None

    def read_state(self) -> StoreState:
        return StoreState(events=self._events, source_version=self._source_version)

    def write_events(self, events: tuple[AuditEvent, ...]) -> None:
        self._events = events
        self._source_version = 2

    def read_index(self) -> dict | None:
        return self._index

    def write_index(self, index: dict) -> None:
        self._index = index


class JsonFileLogStore:
    """A log-store held in a plain JSON file, addressed by ``--log-store``.

    Reads accept either the current format (``store_version: 2``, entries
    already carrying a content-derived ``event_id``) or the older archive
    format (``store_version: 1``, entries keyed by their own ``ref`` and an
    export-observed ``at``). Archive entries are reconciled into canonical
    events before this adapter hands anything back, so callers past this
    point never see the archive shape.

    A missing file reads as an empty, current-format store: there is nothing
    to migrate, and the first ``record`` call creates it.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read_state(self) -> StoreState:
        if not self.path.exists():
            return StoreState(events=(), source_version=2)

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        version = payload.get("store_version", 2)

        if version == 1:
            records = (
                LegacyRecord(
                    ref=entry["ref"],
                    actor=entry["actor"],
                    action=entry["action"],
                    outcome=entry["outcome"],
                    at=entry["at"],
                )
                for entry in payload.get("entries", [])
            )
            return StoreState(events=tuple(reconcile_legacy_records(records)), source_version=1)

        events = tuple(
            AuditEvent(
                event_id=entry["event_id"],
                sequence=entry["sequence"],
                actor=entry["actor"],
                action=entry["action"],
                outcome=entry["outcome"],
                recorded_at=entry["recorded_at"],
                source_version=entry.get("source_version", 2),
                metadata=entry.get("metadata", {}),
            )
            for entry in payload.get("entries", [])
        )
        return StoreState(events=events, source_version=2)

    def write_events(self, events: tuple[AuditEvent, ...]) -> None:
        payload = {
            "store_version": 2,
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
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def read_index(self) -> dict | None:
        index_path = self._index_path()
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8"))

    def write_index(self, index: dict) -> None:
        self._index_path().write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _index_path(self) -> Path:
        return self.path.with_name(self.path.name + ".index.json")


class SqliteLogStore:
    """A log-store held in a SQLite database file.

    Backs the loopback HTTP surface in :mod:`auditlog.httpd`. Read/write
    semantics match :class:`JsonFileLogStore` exactly -- ``write_events``
    replaces the whole canonical event set in one transaction rather than
    appending a row, so both adapters honor the same ``LogStore`` contract
    and ``AuditService`` cannot tell them apart.

    A database that doesn't exist yet is created with an empty schema on
    first connection, so it reads back as an empty, current-format store,
    the same as a missing ``JsonFileLogStore`` path.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS derived_index (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL
                )
                """
            )

    def read_state(self) -> StoreState:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_id, sequence, actor, action, outcome, recorded_at, metadata "
                "FROM events ORDER BY sequence"
            ).fetchall()
        events = tuple(
            AuditEvent(
                event_id=row[0],
                sequence=row[1],
                actor=row[2],
                action=row[3],
                outcome=row[4],
                recorded_at=row[5],
                metadata=json.loads(row[6]),
            )
            for row in rows
        )
        return StoreState(events=events, source_version=2)

    def write_events(self, events: tuple[AuditEvent, ...]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM events")
            conn.executemany(
                "INSERT INTO events (sequence, event_id, actor, action, outcome, recorded_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        event.sequence,
                        event.event_id,
                        event.actor,
                        event.action,
                        event.outcome,
                        event.recorded_at,
                        json.dumps(event.metadata),
                    )
                    for event in events
                ],
            )

    def read_index(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM derived_index WHERE id = 1").fetchone()
        return json.loads(row[0]) if row else None

    def write_index(self, index: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO derived_index (id, payload) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload",
                (json.dumps(index),),
            )
