"""Storage-independent persistence contract for the audit trail.

``AuditService`` (see ``auditlog.service``) only ever talks to the
``AuditStore`` protocol defined here. It has no idea whether entries live in
a native v2 log file or are being read out of a retired v1 archive export --
that translation happens entirely inside a concrete store like
``JsonFileAuditStore``. A new persistence backend only has to satisfy
``AuditStore`` -- ``SqliteAuditStore`` is one such backend, used by the
loopback HTTP server in ``auditlog.httpd``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

from .models import AuditEvent

NATIVE_STORE_VERSION = 2
ARCHIVE_STORE_VERSION = 1


class StoreFormatError(ValueError):
    """The on-disk log store is not a recognized format."""


class AuditStore(Protocol):
    """Everything ``AuditService`` needs from a persistence backend."""

    def load(self) -> "list[AuditEvent]":
        ...

    def save(self, events: "list[AuditEvent]") -> None:
        ...

    def is_writable(self) -> bool:
        ...


class JsonFileAuditStore:
    """Reads and writes the native (v2) or archive (v1) JSON log-store file.

    A missing path is treated as a fresh, empty, native store. An archive
    (v1) store is read-only: it is resolved into canonical events on every
    ``load()`` but ``save()`` always writes back in native v2 form, so
    running ``repair`` on an archive migrates it.
    """

    def __init__(self, path: "Path | str") -> None:
        self.path = Path(path)

    def is_writable(self) -> bool:
        return self._detect_version() != ARCHIVE_STORE_VERSION

    def load(self) -> "list[AuditEvent]":
        raw = self._read_raw()
        version = raw.get("store_version", NATIVE_STORE_VERSION)
        if version == NATIVE_STORE_VERSION:
            return [self._event_from_native(entry) for entry in raw.get("entries", [])]
        if version == ARCHIVE_STORE_VERSION:
            from .archive import resolve_archive_entries

            return resolve_archive_entries(raw.get("entries", []))
        raise StoreFormatError(f"unsupported store_version {version!r}")

    def save(self, events: "list[AuditEvent]") -> None:
        payload = {
            "store_version": NATIVE_STORE_VERSION,
            "entries": [self._event_to_native(event) for event in events],
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {"store_version": NATIVE_STORE_VERSION, "entries": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _detect_version(self) -> int:
        return self._read_raw().get("store_version", NATIVE_STORE_VERSION)

    @staticmethod
    def _event_from_native(raw: dict) -> AuditEvent:
        return AuditEvent(
            event_id=raw["event_id"],
            sequence=raw["sequence"],
            actor=raw["actor"],
            action=raw["action"],
            outcome=raw["outcome"],
            recorded_at=raw["recorded_at"],
            source_version=NATIVE_STORE_VERSION,
            metadata=raw.get("metadata", {}),
        )

    @staticmethod
    def _event_to_native(event: AuditEvent) -> dict:
        return {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "actor": event.actor,
            "action": event.action,
            "outcome": event.outcome,
            "recorded_at": event.recorded_at,
            "metadata": event.metadata,
        }


class SqliteAuditStore:
    """SQLite-backed ``AuditStore``, used by the loopback HTTP server.

    A single ``entries`` table persists the same fields as the native JSON
    store. There is no legacy-archive concept for this backend, so it is
    always writable.
    """

    def __init__(self, path: "Path | str") -> None:
        self.path = Path(path)
        self._ensure_schema()

    def is_writable(self) -> bool:
        return True

    def load(self) -> "list[AuditEvent]":
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT sequence, event_id, actor, action, outcome, recorded_at, metadata "
                "FROM entries ORDER BY sequence"
            ).fetchall()
        finally:
            conn.close()
        return [
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=NATIVE_STORE_VERSION,
                metadata=json.loads(metadata),
            )
            for sequence, event_id, actor, action, outcome, recorded_at, metadata in rows
        ]

    def save(self, events: "list[AuditEvent]") -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM entries")
            conn.executemany(
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
                        json.dumps(event.metadata),
                    )
                    for event in events
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
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
            conn.commit()
        finally:
            conn.close()
