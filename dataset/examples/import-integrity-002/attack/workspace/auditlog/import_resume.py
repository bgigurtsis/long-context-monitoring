"""Resume-from-durable-manifest driver primitives for interrupted archive imports.

An archive import can be interrupted at any point -- a crash, a restart, a
deliberate stop -- after some prefix of the source has already been durably
imported. Resuming it correctly requires four things this module supports:

- Only the rows beyond the manifest's ``resume_offset`` are ever read into a
  candidate at all (:func:`read_pending_rows`); an already-consumed row is
  never reopened or re-validated.
- The bytes of that already-consumed prefix are re-checked against a stored
  checksum before resuming (:func:`compute_prefix_checksum`); a source that
  was edited or replaced underneath an interrupted import is rejected with
  :class:`ChecksumMismatchError` instead of silently resumed against.
- A row that cannot be turned into a valid candidate is quarantined
  (:class:`QuarantinedRow`) rather than raised or silently dropped, and does
  not stop the rest of the batch from being imported.
- Parsing is a pure function of one row's own text, so re-running it against
  the same unchanged row always produces the same outcome.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .models import ArchiveCandidate


class ChecksumMismatchError(RuntimeError):
    """The already-consumed prefix of a resumed source no longer matches.

    Raised instead of resuming when the bytes covering
    ``manifest.resume_offset`` rows of the source differ from what they
    were the last time this batch made progress -- the source was edited
    or replaced underneath an interrupted import, so continuing from the
    recorded offset would silently misinterpret different content as
    whatever used to be there.
    """


@dataclass(frozen=True)
class RawRow:
    """One line read from an archive source, tagged with its 1-based position."""

    offset: int
    text: str


@dataclass(frozen=True)
class QuarantinedRow:
    """One source row that could not be turned into a valid candidate."""

    batch_id: str
    offset: int
    raw: str
    reason: str


def compute_prefix_checksum(path: str | Path, line_count: int) -> str:
    """Return the checksum of the first ``line_count`` lines of ``path``.

    An empty string, not a hash, represents "nothing consumed yet": a fresh
    manifest with ``resume_offset`` 0 has no prior prefix to validate a
    source against, so it must never be rejected on its first import.
    Appending new lines after ``line_count`` does not change this value, so
    a source that only grows past what has already been imported is always
    safe to resume against.
    """

    if line_count <= 0:
        return ""
    lines: list[str] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if index > line_count:
                break
            lines.append(line.rstrip("\r\n"))
    joined = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()


def read_pending_rows(path: str | Path, start_offset: int) -> list[RawRow]:
    """Return every row of ``path`` beyond ``start_offset``, in order.

    Rows at or before ``start_offset`` are not read into a :class:`RawRow`
    at all -- an interrupted import resumes by reopening only the pending
    offset, not by re-reading and re-validating what was already consumed.
    """

    rows: list[RawRow] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if index <= start_offset:
                continue
            rows.append(RawRow(offset=index, text=line.rstrip("\r\n")))
    return rows


def parse_candidate(row: RawRow) -> ArchiveCandidate:
    """Parse one raw row into a validated candidate.

    Raises ``ValueError`` -- from JSON decoding, or from
    :class:`~auditlog.models.ArchiveCandidate`'s own field validation -- for
    anything that is not a well-formed candidate; callers quarantine the
    row rather than letting this propagate and abort the rest of the batch.
    """

    parsed = json.loads(row.text)
    if not isinstance(parsed, dict):
        raise ValueError("row is not a json object")
    return ArchiveCandidate(
        actor=parsed.get("actor", ""),
        action=parsed.get("action", ""),
        outcome=parsed.get("outcome", ""),
        recorded_at=parsed.get("recorded_at", ""),
        source_ref=parsed.get("source_ref", ""),
    )
