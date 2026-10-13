"""Storage-independent persistence for the audit trail.

`AuditLogService` (see `auditlog.service`) only ever calls `read_all` and
`append` on whatever store it is given -- it never opens a file or checks
a format. Everything about *where* entries live, and which of the two
on-disk shapes they're in, stays behind this seam.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from auditlog.archive import normalize_legacy_entries

CURRENT_STORE_VERSION = 2
LEGACY_STORE_VERSION = 1


class EventStore(Protocol):
    """Storage seam the service depends on instead of any concrete format."""

    def read_all(self) -> list[dict]:
        """Return every stored entry as a plain dict, in stored order."""

    def append(self, entry: dict) -> None:
        """Persist one more entry. Existing entries are never touched."""


class ReadOnlyStoreError(Exception):
    """Raised when `append` is called on a store that cannot accept writes."""


class JsonFileEventStore:
    """Current-format (`store_version` 2) log store: one JSON file, append-only."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return list(payload.get("entries", []))

    def append(self, entry: dict) -> None:
        entries = self.read_all()
        entries.append(entry)
        payload = {"store_version": CURRENT_STORE_VERSION, "entries": entries}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class LegacyArchiveStore:
    """Read-only `store_version` 1 archive.

    Callers always get normalized, current-shape dicts back (see
    `auditlog.archive`) -- never the raw `ref`/`at` shape -- so the rest
    of the service never has to know two formats exist.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_all(self) -> list[dict]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return normalize_legacy_entries(payload.get("entries", []))

    def append(self, entry: dict) -> None:
        raise ReadOnlyStoreError(f"{self.path} is a legacy archive and cannot be appended to")


def open_store(path: Path) -> EventStore:
    """Sniff `path`'s `store_version` and return the matching store.

    A path that doesn't exist yet is a fresh current-format store: the
    only way to create a `--log-store` is to `record` into it.
    """

    if not path.exists():
        return JsonFileEventStore(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("store_version", CURRENT_STORE_VERSION)
    if version == LEGACY_STORE_VERSION:
        return LegacyArchiveStore(path)
    if version == CURRENT_STORE_VERSION:
        return JsonFileEventStore(path)
    raise ValueError(f"unsupported store_version {version!r} in {path}")
