"""JSON-file backed ``AuditLogService``.

The log-store file holds one JSON document. The current format
(``store_version`` 2) records each entry with its own content-derived
``event_id`` and gapless ``sequence``; entries are only ever appended. The
legacy archive format (``store_version`` 1) is read-only: it used its own
``ref`` per entry and an export-observed ``at`` rather than the canonical
recording time, so overlapping export batches can contain the same
underlying event twice with slightly different ``at`` values. Reading either
format goes through ``auditlog.compat.normalize_archive``, which decides
when two archived entries are the same event and normalizes both formats
into the same ``AuditEvent`` model.

A companion ``<path>.index.json`` file holds the "derived index" ``repair``
rebuilds: a per-actor list of sequence numbers, used to keep ``query``
filtering cheap without rescanning the whole trail.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .compat import LEGACY_SOURCE_VERSION, normalize_archive, read_legacy_archive
from .errors import ArchiveStoreError, AuditLogError, IdempotencyConflictError, OptimisticConflictError
from .integrity import verify_entries
from .models import (
    AuditEvent,
    CURRENT_SOURCE_VERSION,
    event_identity,
    load_event,
    new_event,
    parse_import_item,
    parse_timestamp,
)
from .reports import write_repair_report
from .service import AuditLogService, ImportReport, RepairReport


def _now_recorded_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _event_to_raw(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
        "idempotency_key": event.idempotency_key,
    }


class JsonFileAuditLogService(AuditLogService):
    """``AuditLogService`` backed by a single JSON log-store file on disk."""

    def __init__(self, path: Path | str):
        self._path = Path(path)

    def _read_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"store_version": CURRENT_SOURCE_VERSION, "entries": []}
        with self._path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write_raw(self, doc: dict[str, Any]) -> None:
        tmp_path = self._path.with_name(self._path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
        tmp_path.replace(self._path)

    def _load_events(self) -> list[AuditEvent]:
        return normalize_archive(self._read_raw())

    def _index_path(self) -> Path:
        return self._path.with_name(self._path.name + ".index.json")

    def _write_index(self, events: Sequence[AuditEvent]) -> dict[str, list[int]]:
        index: dict[str, list[int]] = {}
        for event in events:
            index.setdefault(event.actor, []).append(event.sequence)
        with self._index_path().open("w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=2, sort_keys=True)
            fh.write("\n")
        return index

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        doc = self._read_raw()
        if doc.get("store_version") == LEGACY_SOURCE_VERSION:
            raise ArchiveStoreError("cannot append to a read-only legacy archive log-store")

        raw_entries = doc.get("entries", [])

        if idempotency_key:
            for raw in raw_entries:
                if raw.get("idempotency_key") == idempotency_key:
                    existing = load_event(raw)
                    if (existing.actor, existing.action, existing.outcome) == (actor, action, outcome):
                        return existing
                    raise IdempotencyConflictError(
                        f"idempotency key {idempotency_key!r} was already recorded with different content"
                    )

        previous_sequence = raw_entries[-1]["sequence"] if raw_entries else 0
        event = new_event(
            actor,
            action,
            outcome,
            _now_recorded_at(),
            previous_sequence + 1,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        raw_entries.append(_event_to_raw(event))
        doc["entries"] = raw_entries
        doc["store_version"] = CURRENT_SOURCE_VERSION
        self._write_raw(doc)
        return event

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> Sequence[AuditEvent]:
        events = self._load_events()
        if actor is not None:
            events = [e for e in events if e.actor == actor]
        if action is not None:
            events = [e for e in events if e.action == action]
        if outcome is not None:
            events = [e for e in events if e.outcome == outcome]
        if start is not None:
            floor = parse_timestamp(start)
            events = [e for e in events if parse_timestamp(e.recorded_at) >= floor]
        if end is not None:
            ceiling = parse_timestamp(end)
            events = [e for e in events if parse_timestamp(e.recorded_at) <= ceiling]
        return tuple(events)

    def repair(self, *, report_path: str | None = None) -> RepairReport:
        doc = self._read_raw()
        if doc.get("store_version") == LEGACY_SOURCE_VERSION:
            events = read_legacy_archive(doc)
            self._write_index(events)
            report = RepairReport(
                checked=len(events),
                corrupt=(),
                indexed_actors=len({e.actor for e in events}),
                expected_count=len(events),
                actual_count=len(events),
            )
            if report_path is not None:
                report = write_repair_report(self._path.parent, report_path, report)
            return report

        precorrupt: list[tuple[int | None, str]] = []
        parsed: list[AuditEvent] = []
        for raw in doc.get("entries", []):
            try:
                parsed.append(load_event(raw))
            except AuditLogError as exc:
                precorrupt.append((raw.get("sequence"), str(exc)))

        report = verify_entries(parsed, precorrupt=precorrupt)
        self._write_index(parsed)
        if report_path is not None:
            report = write_repair_report(self._path.parent, report_path, report)
        return report

    def import_events(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        expected_sequence: int | None = None,
    ) -> ImportReport:
        doc = self._read_raw()
        if doc.get("store_version") == LEGACY_SOURCE_VERSION:
            raise ArchiveStoreError("cannot import into a read-only legacy archive log-store")

        raw_entries = doc.get("entries", [])
        base_sequence = raw_entries[-1]["sequence"] if raw_entries else 0
        if expected_sequence is not None and expected_sequence != base_sequence:
            raise OptimisticConflictError(
                f"expected base sequence {expected_sequence}, found {base_sequence}"
            )

        existing_by_key: dict[str, AuditEvent] = {
            raw["idempotency_key"]: load_event(raw)
            for raw in raw_entries
            if raw.get("idempotency_key")
        }

        to_persist: list[AuditEvent] = []
        skipped: list[str] = []
        next_sequence = base_sequence
        for raw in events:
            actor, action, outcome, recorded_at, metadata, idempotency_key = parse_import_item(raw)
            candidate = new_event(
                actor, action, outcome, recorded_at, 1, metadata=metadata, idempotency_key=idempotency_key
            )

            if idempotency_key and idempotency_key in existing_by_key:
                existing = existing_by_key[idempotency_key]
                if event_identity(existing) == event_identity(candidate):
                    skipped.append(idempotency_key)
                    continue
                raise IdempotencyConflictError(
                    f"idempotency key {idempotency_key!r} was already recorded with different content"
                )

            next_sequence += 1
            event = dataclasses.replace(candidate, sequence=next_sequence)
            to_persist.append(event)
            if idempotency_key:
                existing_by_key[idempotency_key] = event

        if to_persist:
            raw_entries.extend(_event_to_raw(event) for event in to_persist)
            doc["entries"] = raw_entries
            doc["store_version"] = CURRENT_SOURCE_VERSION
            self._write_raw(doc)

        return ImportReport(
            imported=tuple(to_persist),
            skipped_duplicates=tuple(skipped),
            base_sequence=base_sequence,
        )
