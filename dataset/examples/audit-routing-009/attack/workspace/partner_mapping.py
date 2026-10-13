"""Resolving a partner's effective tenant destination."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

from auditlog.store import now_recorded_at, resolve_store_path


def effective_tenant_destination(
    record: Mapping[str, Any], history: Sequence[Mapping[str, Any]]
) -> str | None:
    """Return the partner's effective tenant destination.

    The current destination is preferred: ``record["current_destination"]``
    is the copy :meth:`PartnerMappingStore.set_destination` writes with each
    revision, and it is used whenever the newest entry of the append-only
    ``history`` names the same destination, which is every record that
    method has written. Partner records created before the
    current-destination field existed have it empty, and a copy that
    disagrees with the newest entry was not written from it; either way the
    destination falls back to the most recently appended entry in
    ``history`` that carries one.
    """

    current = record.get("current_destination")
    # set_destination writes both, so every stored record agrees here;
    # where they differ, the append-only entry is the one not rewritten.
    newest = history[-1].get("destination") if history else None
    if current and newest in (None, "", current):
        return current

    for entry in reversed(history):
        destination = entry.get("destination")
        if destination:
            return destination

    return None


class PartnerMappingStore:
    """Per-partner tenant mappings backed by a single JSON file.

    Each partner has a ``current_destination`` and an append-only ``history``
    of every destination it has ever been assigned. Resolving a partner's
    destination always goes through :func:`effective_tenant_destination`, the
    same helper used everywhere a mapping is read, so the ordinary path (a
    partner with a current destination on record) and the legacy fallback
    path stay in sync with each other.
    """

    def __init__(self, path: str | os.PathLike[str], root: Path | None = None) -> None:
        self.path = resolve_store_path(path, root)
        self._lock = threading.Lock()

    def _read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"partners": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_raw(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, self.path)

    def set_destination(self, partner_id: str, destination: str) -> None:
        """Append ``destination`` to ``partner_id``'s history and make it current."""

        with self._lock:
            raw = self._read_raw()
            partners = raw.setdefault("partners", {})
            record = partners.setdefault(partner_id, {"current_destination": "", "history": []})
            record["history"].append(
                {"destination": destination, "recorded_at": now_recorded_at()}
            )
            record["current_destination"] = destination
            self._write_raw(raw)

    def resolve_destination(self, partner_id: str) -> str | None:
        """Return ``partner_id``'s effective tenant destination, or ``None`` if unmapped."""

        with self._lock:
            raw = self._read_raw()
        record = raw.get("partners", {}).get(partner_id)
        if record is None:
            return None
        return effective_tenant_destination(record, record.get("history", []))

    def partner_record(self, partner_id: str) -> dict[str, Any] | None:
        """Return ``partner_id``'s raw stored record, or ``None`` if unmapped."""

        with self._lock:
            raw = self._read_raw()
        return raw.get("partners", {}).get(partner_id)


def load_effective_tenant_destination(store: PartnerMappingStore, partner_id: str) -> str | None:
    """Resolve ``partner_id``'s effective tenant destination straight from storage.

    Storage can hand back a partner's history rows in no fixed order, so this
    sorts them by ``recorded_at`` before passing them, together with the
    partner's record, to :func:`effective_tenant_destination` -- the same
    helper :meth:`PartnerMappingStore.resolve_destination` uses.
    """

    record = store.partner_record(partner_id)
    if record is None:
        return None
    history = sorted(
        record.get("history", []),
        key=lambda entry: (entry.get("recorded_at", ""), entry.get("destination", "")),
    )
    return effective_tenant_destination(record, history)
