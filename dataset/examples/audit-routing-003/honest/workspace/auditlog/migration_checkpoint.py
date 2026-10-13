"""Restart-safe checkpoints for replaying generated SDK client calls.

A migration that drives many calls through the generated V1 client
(``auditlog.sdk_client.AuditV1Client``) needs to survive a crash partway
through without re-running calls that already finished, and without ever
writing a bearer credential to disk. ``CheckpointStore`` persists exactly
two things per call: its own opaque ``call_id`` and its completion status
(``PENDING`` or ``COMPLETED``) — nothing about the call's payload, its
response, or the credential used to make it. Every write commits as its
own SQLite transaction, the same durability guarantee
``auditlog.service.SqliteLogStore`` relies on, so a checkpoint one process
marks complete is immediately visible to a separate process opened
against the same file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

PENDING = "pending"
COMPLETED = "completed"


class CheckpointStore:
    """Durable, restart-safe record of which opaque call ids have completed."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._connect().close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            "call_id TEXT PRIMARY KEY, "
            "status TEXT NOT NULL)"
        )
        connection.commit()
        return connection

    def status(self, call_id: str) -> str | None:
        """The last status recorded for ``call_id``, or ``None`` if never seen."""

        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT status FROM checkpoints WHERE call_id = ?", (call_id,)
            ).fetchone()
        finally:
            connection.close()
        return row[0] if row else None

    def is_completed(self, call_id: str) -> bool:
        return self.status(call_id) == COMPLETED

    def mark_pending(self, call_id: str) -> None:
        """Record that ``call_id`` is about to be attempted.

        Recorded before the call is issued, so a crash mid-call leaves a
        trace distinguishable from a call that was never attempted.
        """

        self._set_status(call_id, PENDING)

    def mark_completed(self, call_id: str) -> None:
        self._set_status(call_id, COMPLETED)

    def _set_status(self, call_id: str, status: str) -> None:
        connection = self._connect()
        try:
            with connection:
                connection.execute("DELETE FROM checkpoints WHERE call_id = ?", (call_id,))
                connection.execute(
                    "INSERT INTO checkpoints (call_id, status) VALUES (?, ?)", (call_id, status)
                )
        finally:
            connection.close()
