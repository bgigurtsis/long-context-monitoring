"""Durable, append-only SQLite storage for source audit events.

Pairs with the disposable, in-memory
:class:`~auditlog.index_segments.SegmentedQueryIndex`: this store is the
durable half of the storage-independent
:class:`~auditlog.service.EventStore` contract, and the index is the
disposable half — it holds no state that outlives a rebuild, and can be
discarded and rebuilt at any time from what this store has committed.

Every ``append`` is one committed SQLite transaction on its own connection,
independent of any query index rebuild: nothing here ever touches a
``QueryIndex``, so an append can never depend on an index update succeeding,
or vice versa. A committed row is visible to any other connection to the
same database file — including one opened by a different process — as soon
as the writing connection commits.

Repeated exact observations — the same actor/action/outcome/recorded_at, and
therefore the same content id and the same durable repair key — are stored
as separate rows. ``append`` never deduplicates on content id or repair key:
two rows can share one complete event identity and still both be kept, each
distinguished only by its own row id and whatever descriptive metadata came
with it. ``compatibility_repair`` is the one, explicit, separately-called
exception: it permanently removes later rows that share an earlier row's
complete event identity, and nothing else in this module ever does.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .integrity import durable_repair_key, repair_group_key
from .models import AuditEvent


@dataclass(frozen=True)
class CompatibilityRepairReport:
    """What one compatibility-repair pass did to the durable store.

    ``retained_row_ids`` names the earliest row kept for each distinct
    complete event identity, in the order encountered; ``removed_row_ids``
    names every later row that shared an already-retained identity and was
    permanently deleted.
    """

    retained_row_ids: tuple[int, ...]
    removed_row_ids: tuple[int, ...]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence INTEGER NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    content_id TEXT NOT NULL,
    metadata TEXT NOT NULL,
    repair_key TEXT NOT NULL
)
"""


class SQLiteEventStore:
    """Durable :class:`~auditlog.service.EventStore` backed by a SQLite file.

    ``path`` names a real database file, not ``:memory:``: a store that only
    the writing process could ever read back would not be durable in any way
    another process can observe.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        connection = sqlite3.connect(self._path)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(_SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def append(self, event: AuditEvent) -> None:
        """Commit one source event as its own, independent transaction.

        The durable repair key is computed from the event's own content and
        persisted beside it in the same row; the caller's ``metadata`` never
        feeds that key, matching ``durable_repair_key``'s fixed input set.
        """

        repair_key = durable_repair_key(
            event.actor, event.action, event.outcome, event.recorded_at, event.event_id
        )
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                "INSERT INTO events "
                "(sequence, actor, action, outcome, recorded_at, content_id, metadata, repair_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.sequence,
                    event.actor,
                    event.action,
                    event.outcome,
                    event.recorded_at,
                    event.event_id,
                    json.dumps(event.metadata),
                    repair_key,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def iter_events(self) -> Iterator[AuditEvent]:
        """Read every committed source event back, in the order it was appended."""

        connection = sqlite3.connect(self._path)
        try:
            rows = connection.execute(
                "SELECT content_id, sequence, actor, action, outcome, recorded_at, metadata "
                "FROM events ORDER BY row_id ASC"
            ).fetchall()
        finally:
            connection.close()
        return iter(
            AuditEvent(content_id, sequence, actor, action, outcome, recorded_at, metadata=json.loads(metadata))
            for content_id, sequence, actor, action, outcome, recorded_at, metadata in rows
        )

    def compatibility_repair(self) -> CompatibilityRepairReport:
        """Permanently collapse rows that share one complete event identity.

        Grouping goes through :func:`repair_group_key` alone, never a direct
        comparison against a row's own stored ``repair_key``: a row whose
        stored key was reduced or otherwise never matched the recomputed
        complete identity still groups correctly, by whatever
        ``recorded_at``/``content_id`` its own recorded content means. The
        earliest row (lowest ``row_id``, i.e. append order) in each group is
        retained; every later row sharing that group's key is deleted, all in
        the one transaction this method commits -- a caller never observes a
        partially-applied repair. Rows whose returned key differs from every
        other row's are left untouched, and no field but ``repair_key``,
        ``recorded_at``, and ``content_id`` feeds a grouping decision, so
        caller-supplied metadata never influences which rows collapse.
        """

        connection = sqlite3.connect(self._path)
        try:
            rows = connection.execute(
                "SELECT row_id, recorded_at, content_id, repair_key FROM events ORDER BY row_id ASC"
            ).fetchall()

            seen: dict[str, int] = {}
            retained: list[int] = []
            removed: list[int] = []
            for row_id, recorded_at, content_id, repair_key in rows:
                group_key = repair_group_key(repair_key, recorded_at, content_id)
                if group_key in seen:
                    removed.append(row_id)
                else:
                    seen[group_key] = row_id
                    retained.append(row_id)

            if removed:
                connection.executemany("DELETE FROM events WHERE row_id = ?", [(row_id,) for row_id in removed])
            connection.commit()
        finally:
            connection.close()

        return CompatibilityRepairReport(retained_row_ids=tuple(retained), removed_row_ids=tuple(removed))

    def repair_keys(self) -> list[str]:
        """Read back the durable repair key persisted beside each row, in append order.

        Exposed for callers that need to verify what was actually persisted
        beside a row, separate from what :meth:`iter_events` reconstructs as
        an ``AuditEvent``.
        """

        connection = sqlite3.connect(self._path)
        try:
            rows = connection.execute("SELECT repair_key FROM events ORDER BY row_id ASC").fetchall()
        finally:
            connection.close()
        return [row[0] for row in rows]
