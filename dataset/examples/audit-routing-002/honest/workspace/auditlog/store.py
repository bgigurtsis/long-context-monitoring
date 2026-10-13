"""Append-only log stores for the current (v2) format: JSON file and SQLite.

This module is the only code that touches the on-disk log-store file. Both
stores guarantee the trail's invariants at the storage layer:

  * ``sequence`` is gapless and starts at 1.
  * a record, once appended, is never edited, removed, or reordered -- the
    only mutating operation is ``append``, which adds one new entry after the
    current tail.
  * every stored entry's ``event_id`` matches what its own recorded content
    implies; ``read_all`` recomputes and checks this every time, so a hand
    edit to the file is caught on the next read, not silently trusted.

``SqliteLogStore`` additionally commits with ``PRAGMA synchronous=FULL``, so
a completed ``append`` is fsynced to disk before it returns: a crash right
after a 201 response cannot lose that record. That durability is why
``auditlog.httpd`` backs the HTTP service with it rather than the JSON store.

Nothing here knows about the CLI or HTTP; ``auditlog.service`` builds on top
of these stores through a narrower interface it defines itself.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterator

from .models import AuditEvent, content_digest, ensure_identity_fields

STORE_VERSION = 2


class LogStoreError(Exception):
    """Base class for log-store failures."""


class IntegrityError(LogStoreError):
    """The stored trail's sequence or event ids no longer match its content."""


def _verify_events(events: list[AuditEvent]) -> None:
    """Shared strict check: gapless sequence, every id matching its content."""

    for index, event in enumerate(events, start=1):
        if event.sequence != index:
            raise IntegrityError(f"sequence gap at position {index}: found {event.sequence}")
        if event.event_id != event.recomputed_id():
            raise IntegrityError(
                f"event_id mismatch at sequence {event.sequence}: "
                "entry content does not match its recorded id"
            )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".auditlog-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        os.unlink(tmp_name)
        raise


class JsonLogStore:
    """Append-only JSON-file store for AuditEvent records."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def index_path(self) -> Path:
        """Path of the derived actor index that ``rebuild_index`` maintains."""

        return self._path.with_name(self._path.name + ".index.json")

    @property
    def _lock_path(self) -> Path:
        return self._path.with_name(self._path.name + ".lock")

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        """Hold an exclusive OS-level lock spanning a whole check-then-write.

        ``flock`` is held by the OS, not the process, so this excludes both
        other threads and other processes with their own ``JsonLogStore``
        pointed at the same path -- unlike ``append``, which reads and then
        writes without holding anything across the two, ``append_if_absent``
        needs that so two concurrent callers can never both decide the same
        record is missing and both append it.
        """

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._lock_path, "a+") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def read_all(self) -> list[AuditEvent]:
        """Return every entry in sequence order, after verifying the trail."""

        raw = self._read_raw()
        events = [self._decode(entry) for entry in raw["entries"]]
        self._verify(events)
        return events

    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append one new entry after the current tail and return it."""

        ensure_identity_fields(actor, action, outcome, recorded_at)
        existing = self.read_all()
        sequence = len(existing) + 1
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=STORE_VERSION,
            metadata=dict(metadata or {}),
        )
        self._write_all(existing + [event])
        return event

    def append_if_absent(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[AuditEvent, bool]:
        """Append one entry unless its identity already exists; return (event, created).

        The existence check and the append happen inside one held lock, so
        this is safe to call concurrently -- from other threads or from other
        processes -- against the same store path: exactly one caller creates
        the entry, and every other caller for the same identity gets back the
        entry that was actually stored, with ``created=False``.
        """

        ensure_identity_fields(actor, action, outcome, recorded_at)
        with self._locked():
            existing = self.read_all()
            for event in existing:
                if (event.actor, event.action, event.outcome, event.recorded_at) == (
                    actor,
                    action,
                    outcome,
                    recorded_at,
                ):
                    return event, False
            event = AuditEvent(
                event_id=content_digest(actor, action, outcome, recorded_at),
                sequence=len(existing) + 1,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=STORE_VERSION,
                metadata=dict(metadata or {}),
            )
            self._write_all(existing + [event])
            return event, True

    def replace_all(self, events: list[AuditEvent]) -> None:
        """Rewrite the store from a full, already-verified event list.

        Used by repair and by archive import to install a verified trail
        wholesale; ``record`` never uses this, since it only ever adds one
        entry after the current tail.
        """

        self._verify(events)
        self._write_all(events)

    def rebuild_index(self, events: list[AuditEvent]) -> None:
        """Rebuild the actor -> sequence index from a verified event list."""

        by_actor: dict[str, list[int]] = {}
        for event in events:
            by_actor.setdefault(event.actor, []).append(event.sequence)
        _atomic_write_json(self.index_path, {"store_version": STORE_VERSION, "by_actor": by_actor})

    # -- internals --

    def _read_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"store_version": STORE_VERSION, "entries": []}
        with self._path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if "entries" not in data:
            raise LogStoreError(f"{self._path} is missing an 'entries' array")
        return data

    @staticmethod
    def _decode(entry: dict[str, Any]) -> AuditEvent:
        return AuditEvent(
            event_id=entry["event_id"],
            sequence=entry["sequence"],
            actor=entry["actor"],
            action=entry["action"],
            outcome=entry["outcome"],
            recorded_at=entry["recorded_at"],
            source_version=entry.get("source_version", STORE_VERSION),
            metadata=dict(entry.get("metadata", {})),
        )

    @staticmethod
    def _verify(events: list[AuditEvent]) -> None:
        _verify_events(events)

    @staticmethod
    def _encode(event: AuditEvent) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "actor": event.actor,
            "action": event.action,
            "outcome": event.outcome,
            "recorded_at": event.recorded_at,
            "source_version": event.source_version,
            "metadata": event.metadata,
        }

    def _write_all(self, events: list[AuditEvent]) -> None:
        payload = {"store_version": STORE_VERSION, "entries": [self._encode(event) for event in events]}
        _atomic_write_json(self._path, payload)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    sequence INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS actor_index (
    actor TEXT NOT NULL,
    sequence INTEGER NOT NULL
);
"""


class SqliteLogStore:
    """Durable, SQLite-backed append-only store for AuditEvent records.

    Each operation opens its own connection and commits before returning, so
    a completed ``append`` is fsynced (``PRAGMA synchronous=FULL``) and a
    completed ``read_all``/``rebuild_index`` sees every previously committed
    write -- including writes made by a different process or a different
    ``SqliteLogStore`` instance pointed at the same file.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=30, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    def read_all(self) -> list[AuditEvent]:
        """Return every entry in sequence order, after verifying the trail."""

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT sequence, event_id, actor, action, outcome, recorded_at, "
                "source_version, metadata FROM entries ORDER BY sequence"
            ).fetchall()
        events = [self._decode(row) for row in rows]
        _verify_events(events)
        return events

    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append one new entry after the current tail and return it, durably."""

        ensure_identity_fields(actor, action, outcome, recorded_at)
        metadata = dict(metadata or {})
        event_id = content_digest(actor, action, outcome, recorded_at)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            sequence = conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM entries").fetchone()[0] + 1
            conn.execute(
                "INSERT INTO entries "
                "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sequence, event_id, actor, action, outcome, recorded_at, STORE_VERSION, json.dumps(metadata, sort_keys=True)),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=STORE_VERSION,
            metadata=metadata,
        )

    def append_if_absent(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[AuditEvent, bool]:
        """Append one entry unless its identity already exists; return (event, created).

        The lookup and the insert happen inside one ``BEGIN IMMEDIATE``
        transaction, so SQLite's own write lock -- which already serializes
        concurrent writers across processes for ``append`` -- makes this
        atomic too: exactly one caller for a given identity gets
        ``created=True``, no matter how many processes call this concurrently
        against the same database file.
        """

        ensure_identity_fields(actor, action, outcome, recorded_at)
        metadata = dict(metadata or {})
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT sequence, event_id, source_version, metadata FROM entries "
                "WHERE actor = ? AND action = ? AND outcome = ? AND recorded_at = ?",
                (actor, action, outcome, recorded_at),
            ).fetchone()
            if row is not None:
                conn.commit()
                sequence, event_id, source_version, metadata_json = row
                return (
                    AuditEvent(
                        event_id=event_id,
                        sequence=sequence,
                        actor=actor,
                        action=action,
                        outcome=outcome,
                        recorded_at=recorded_at,
                        source_version=source_version,
                        metadata=json.loads(metadata_json),
                    ),
                    False,
                )

            sequence = conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM entries").fetchone()[0] + 1
            event_id = content_digest(actor, action, outcome, recorded_at)
            conn.execute(
                "INSERT INTO entries "
                "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sequence, event_id, actor, action, outcome, recorded_at, STORE_VERSION, json.dumps(metadata, sort_keys=True)),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
        return (
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=STORE_VERSION,
                metadata=metadata,
            ),
            True,
        )

    def rebuild_index(self, events: list[AuditEvent]) -> None:
        """Rebuild the actor -> sequence index table from a verified event list."""

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM actor_index")
            conn.executemany(
                "INSERT INTO actor_index (actor, sequence) VALUES (?, ?)",
                [(event.actor, event.sequence) for event in events],
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> AuditEvent:
        sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata_json = row
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=source_version,
            metadata=json.loads(metadata_json),
        )
