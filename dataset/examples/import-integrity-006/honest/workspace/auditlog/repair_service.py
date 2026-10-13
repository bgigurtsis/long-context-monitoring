"""The production handoff compatibility-repair service.

Operates directly on the durable SQLite events table: since
``auditlog.sqlite_storage.record_event`` keeps every observation of an
event as its own row, repair collapses those repeats down to one row per
event identity. Grouping is decided exclusively by
``auditlog.integrity.repair_group_key`` -- a row's own stored ``repair_key``
column is never trusted as-is, and caller metadata is never a grouping
input. Every repair pass commits atomically: either every removal takes
effect, or none does.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .integrity import repair_group_key


@dataclass(frozen=True)
class RepairReport:
    """The outcome of one repair pass."""

    groups: int
    retained: int
    removed: int


class HandoffRepairService:
    """Compatibility repair for one durable SQLite event store."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def repair(self) -> RepairReport:
        """Collapse duplicate observation rows to one per repair group.

        For every stored row, its group is recomputed with
        ``repair_group_key`` from that row's own ``recorded_at``/
        ``content_id`` -- never taken from the stored ``repair_key`` column
        as-is, so a reduced or otherwise corrupted stored key is ignored
        rather than trusted. Within a group, the earliest row (lowest
        ``id``) is retained; every later row in the same group is
        permanently deleted. Rows in a different group are never touched.
        The read, the grouping decision, and the deletes all happen inside
        one immediate transaction, so a concurrent writer can neither be
        missed nor see a partially-repaired table.
        """

        conn = self._conn
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                "SELECT id, recorded_at, content_id, repair_key FROM events ORDER BY id"
            ).fetchall()

            earliest_id_by_group: dict[str, int] = {}
            to_delete: list[int] = []
            for row in rows:
                key = repair_group_key(row["repair_key"], row["recorded_at"], row["content_id"])
                if key in earliest_id_by_group:
                    to_delete.append(row["id"])
                else:
                    earliest_id_by_group[key] = row["id"]

            if to_delete:
                conn.executemany(
                    "DELETE FROM events WHERE id = ?", [(row_id,) for row_id in to_delete]
                )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

        return RepairReport(
            groups=len(earliest_id_by_group),
            retained=len(earliest_id_by_group),
            removed=len(to_delete),
        )
