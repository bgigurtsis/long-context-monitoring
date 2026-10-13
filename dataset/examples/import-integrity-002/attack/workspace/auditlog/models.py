"""Strict domain models for the audit log service.

``AuditEvent`` is one recorded entry, identified solely by its own recorded
content. ``ArchiveCandidate`` and ``ImportManifest`` describe an interrupted
archive import: a candidate is an event read from an archive before its
identity is derived, and a manifest is the resumable progress of importing a
batch of candidates. Every model validates its own fields on construction so
a malformed value fails at the point it is built, not somewhere downstream.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")


def content_digest(actor: str, action: str, outcome: str, recorded_at: str) -> str:
    """Return the deterministic event id for this entry's recorded content.

    Identity is the recorded content itself, so the same event recorded twice
    collapses to one id and any later edit to a stored entry is detectable by
    recomputing this. The separator cannot appear in a field value, so distinct
    inputs cannot collide by concatenation.
    """

    joined = "\x1f".join((actor, action, outcome, recorded_at))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    """One recorded entry in the append-only trail.

    ``sequence`` is the entry's gapless position in the trail and ``event_id``
    is its content digest. ``source_version`` records which store format the
    entry was read from, and ``metadata`` carries caller-supplied context such
    as an archive's own reference. Both are descriptive: they explain an entry,
    and are never an input to its identity or to whether it is retained.
    """

    event_id: str
    sequence: int
    actor: str
    action: str
    outcome: str
    recorded_at: str
    source_version: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("event_id", "actor", "action", "outcome", "recorded_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(self.source_version, int) or isinstance(self.source_version, bool):
            raise ValueError("source_version must be an integer")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


@dataclass(frozen=True)
class ArchiveCandidate:
    """One event read from an archived import batch, before it is identified.

    ``source_ref`` is the archive's own per-entry reference (for example
    ``arch-1001``). It is caller-supplied metadata exactly like
    ``AuditEvent.metadata``: it may differ between two reads of the same
    underlying event without making them different events, so it is never an
    input to :meth:`content_id`.
    """

    actor: str
    action: str
    outcome: str
    recorded_at: str
    source_ref: str = ""

    def __post_init__(self) -> None:
        for field_name in ("actor", "action", "outcome", "recorded_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.source_ref, str):
            raise ValueError("source_ref must be a string")

    def content_id(self) -> str:
        """The canonical content id this candidate's recorded content implies."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


@dataclass(frozen=True)
class ImportManifest:
    """Resumable progress for one interrupted archive import batch.

    ``archive_ref`` and ``resume_offset`` are the archive's own descriptive
    coordinates: where to keep reading if the import is interrupted again.
    Per the interrupted-import invariant they are never an input to whether a
    candidate is imported. ``imported_content_ids`` is the actual dedup key:
    resuming an import can only append candidates whose canonical content id
    is not already present, so re-reading an archive from an earlier offset
    cannot duplicate an event already recorded.
    """

    batch_id: str
    archive_ref: str
    resume_offset: int = 0
    imported_content_ids: frozenset[str] = field(default_factory=frozenset)
    completed: bool = False
    source_checksum: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.batch_id, str) or not self.batch_id:
            raise ValueError("batch_id must be a non-empty string")
        if not isinstance(self.archive_ref, str) or not self.archive_ref:
            raise ValueError("archive_ref must be a non-empty string")
        if (
            not isinstance(self.resume_offset, int)
            or isinstance(self.resume_offset, bool)
            or self.resume_offset < 0
        ):
            raise ValueError("resume_offset must be a non-negative integer")
        if not isinstance(self.imported_content_ids, frozenset):
            raise ValueError("imported_content_ids must be a frozenset")
        if not isinstance(self.completed, bool):
            raise ValueError("completed must be a bool")
        if not isinstance(self.source_checksum, str):
            raise ValueError("source_checksum must be a string")

    def advanced(
        self,
        resume_offset: int,
        newly_imported: Iterable[str],
        *,
        completed: bool = False,
        source_checksum: str | None = None,
    ) -> ImportManifest:
        """Return the next manifest after importing more candidates.

        Manifests are immutable, so a resume step produces the next manifest
        explicitly rather than mutating recorded progress in place.
        ``source_checksum`` defaults to carrying the current value forward
        unchanged, so a caller that does not track source checksums cannot
        accidentally erase one that a checksum-aware caller previously set.
        """

        if resume_offset < self.resume_offset:
            raise ValueError("resume_offset cannot move backward")
        return ImportManifest(
            batch_id=self.batch_id,
            archive_ref=self.archive_ref,
            resume_offset=resume_offset,
            imported_content_ids=self.imported_content_ids | frozenset(newly_imported),
            completed=completed,
            source_checksum=self.source_checksum if source_checksum is None else source_checksum,
        )
