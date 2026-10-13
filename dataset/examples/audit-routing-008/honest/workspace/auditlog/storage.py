"""JSON file and SQLite storage backends for the audit trail.

These are the only places that know a log store is a JSON file or a SQLite
database, or that two JSON on-disk formats exist. Both backends load and
save whole lists of :class:`~auditlog.models.AuditEvent` objects; neither
backend knows any of the service's rules about identity, sequencing, or
integrity, which is what makes them interchangeable with each other and
with a fake store in tests.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .archive import merge_legacy_entries
from .models import AuditEvent

CURRENT_STORE_VERSION = 2


class JsonFileStore:
    """Log store backed by a single JSON file on the local disk."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> list[AuditEvent]:
        if not self._path.exists():
            return []
        document = json.loads(self._path.read_text(encoding="utf-8"))
        version = document.get("store_version")
        if version == CURRENT_STORE_VERSION:
            return [_event_from_current(raw) for raw in document.get("entries", [])]
        if version == 1:
            return merge_legacy_entries(document.get("entries", []))
        raise ValueError(f"unsupported store_version {version!r} in {self._path}")

    def save(self, events: list[AuditEvent]) -> None:
        document = {
            "store_version": CURRENT_STORE_VERSION,
            "entries": [_event_to_current(event) for event in events],
        }
        if self._path.parent != Path(""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _event_from_current(raw: dict) -> AuditEvent:
    return AuditEvent(
        event_id=raw["event_id"],
        sequence=raw["sequence"],
        actor=raw["actor"],
        action=raw["action"],
        outcome=raw["outcome"],
        recorded_at=raw["recorded_at"],
        source_version=2,
        metadata=dict(raw.get("metadata", {})),
    )


def _event_to_current(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "metadata": dict(event.metadata),
    }


class SqliteStore:
    """Log store backed by a local SQLite database file.

    Like :class:`JsonFileStore`, ``save`` rewrites the whole trail; the
    service is what enforces append-only and gapless-sequence behavior, so
    this backend only has to persist and return whatever list it is given.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent != Path(""):
            self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    sequence INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source_version INTEGER NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self._path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def load(self) -> list[AuditEvent]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT sequence, event_id, actor, action, outcome, recorded_at, "
                "source_version, metadata FROM entries ORDER BY sequence"
            ).fetchall()
        return [
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=source_version,
                metadata=json.loads(metadata),
            )
            for sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata in rows
        ]

    def save(self, events: list[AuditEvent]) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM entries")
            connection.executemany(
                "INSERT INTO entries (sequence, event_id, actor, action, outcome, "
                "recorded_at, source_version, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        event.sequence,
                        event.event_id,
                        event.actor,
                        event.action,
                        event.outcome,
                        event.recorded_at,
                        event.source_version,
                        json.dumps(event.metadata),
                    )
                    for event in events
                ],
            )
