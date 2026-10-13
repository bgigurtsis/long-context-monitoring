"""Restart-safe import of mesh-forwarded audit requests.

A mesh sidecar forwards audit requests as envelopes carrying a request id,
the raw (pre-normalization) request path, and the event content itself. The
importer must be safe to kill and restart at any point: replaying the same
envelope after a crash must never append a second event, and two envelopes
that reuse a request id for two different paths must be refused as a
conflict rather than silently overwriting what the id already means.

Idempotency cannot be built on the trail's own event identity, because
``AuditService`` intentionally allows the same content to be recorded twice
as two distinct sequence positions (see ``auditlog.service``) -- so a mesh
request id is tagged onto the recorded event's own ``metadata`` (which is
descriptive and never an input to identity) and reconciliation always looks
up a request id by that tag, never by guessing from content.

A durable ``MeshImportLedger`` records only a request's id, its canonical
path, and its completion status (plus the event_id/sequence once
completed). It has no column for a bearer token, and nothing in this
module's public API accepts one -- an envelope carrying one is rejected
outright by ``parse_mesh_envelope`` before anything is persisted.

This module only ever appends through ``AuditService.record`` and reads
through ``AuditService.query``; it never rewrites or reorders a stored
event, so the trail's immutability and gapless sequence are preserved by
construction.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import AuditEvent
from .paths import canonical_path
from .service import AuditService

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"

# Reserved metadata key an appended event is tagged with, so a crash-recovery
# pass can find "the event this specific request produced" without guessing
# from content -- content alone is not a reliable identity here since the
# trail allows identical content to be recorded more than once.
MESH_REQUEST_ID_METADATA_KEY = "_mesh_request_id"

_MESH_REQUIRED_FIELDS = ("request_id", "path", "actor", "action", "outcome", "recorded_at")
_MESH_ALLOWED_FIELDS = frozenset(_MESH_REQUIRED_FIELDS + ("metadata",))


class MeshImportError(Exception):
    """Base class for mesh import failures."""


class MeshEnvelopeError(MeshImportError):
    """The mesh envelope is not well-formed.

    Any field outside the explicit allow-list -- including a bearer token
    or other auth-forwarding hint a mesh sidecar might embed -- is rejected
    here, before the envelope is parsed any further.
    """


class MeshImportConflictError(MeshImportError):
    """A request id was reused for a different canonical path.

    A request id is only ever a duplicate of itself; if it now resolves to
    a different path than the one already on record, that is a conflicting
    reuse of the id, not a replay of the same request.
    """


@dataclass(frozen=True)
class ParsedMeshEnvelope:
    request_id: str
    path: str
    actor: str
    action: str
    outcome: str
    recorded_at: str
    metadata: "dict[str, str]"


@dataclass(frozen=True)
class LedgerRecord:
    """One persisted row: a request id, its canonical path, and its status.

    ``event_id``/``sequence`` are populated only once ``status`` is
    ``STATUS_COMPLETED``. There is deliberately no field here for a bearer
    token or any other credential.
    """

    request_id: str
    canonical_path: str
    status: str
    event_id: "str | None"
    sequence: "int | None"


@dataclass(frozen=True)
class MeshImportResult:
    """Outcome of one ``import_mesh_request`` call.

    ``replayed`` is ``True`` when no new event was appended by this call --
    the request id was already completed, or crash recovery found that it
    had already been appended -- and ``False`` only when this call is the
    one that performed the append.
    """

    request_id: str
    canonical_path: str
    event: AuditEvent
    replayed: bool


def parse_mesh_envelope(raw: "dict[str, Any]") -> ParsedMeshEnvelope:
    """Strictly parse a mesh import envelope.

    Only the fields the import needs are accepted; a bearer token or any
    other unexpected field makes the whole envelope rejected rather than
    silently dropped, so nothing outside the allow-list can ever reach the
    ledger or the audit trail.
    """

    if not isinstance(raw, dict):
        raise MeshEnvelopeError("envelope must be an object")

    unexpected = set(raw) - _MESH_ALLOWED_FIELDS
    if unexpected:
        raise MeshEnvelopeError(f"unexpected field(s): {sorted(unexpected)}")

    for field in _MESH_REQUIRED_FIELDS:
        if field not in raw:
            raise MeshEnvelopeError(f"missing required field: {field!r}")
        if not isinstance(raw[field], str) or not raw[field]:
            raise MeshEnvelopeError(f"field {field!r} must be a non-empty string")

    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()
    ):
        raise MeshEnvelopeError("field 'metadata' must be an object of string to string")
    if MESH_REQUEST_ID_METADATA_KEY in metadata:
        raise MeshEnvelopeError(f"metadata key {MESH_REQUEST_ID_METADATA_KEY!r} is reserved")

    return ParsedMeshEnvelope(
        request_id=raw["request_id"],
        path=raw["path"],
        actor=raw["actor"],
        action=raw["action"],
        outcome=raw["outcome"],
        recorded_at=raw["recorded_at"],
        metadata=dict(metadata),
    )


class MeshImportLedger:
    """Durable idempotency ledger for mesh request imports.

    Backed by SQLite so a second process opening the same path sees every
    completed or in-flight request the first process recorded -- there is
    no in-memory state a restart could lose. Each operation opens and
    closes its own connection, matching ``SqliteAuditStore``'s pattern.
    """

    def __init__(self, path: "Path | str") -> None:
        self.path = Path(path)
        self._ensure_schema()

    def get(self, request_id: str) -> "LedgerRecord | None":
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT request_id, canonical_path, status, event_id, sequence "
                "FROM mesh_imports WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        request_id, canonical_path_, status, event_id, sequence = row
        return LedgerRecord(request_id, canonical_path_, status, event_id, sequence)

    def mark_pending(self, request_id: str, canonical_path_: str) -> None:
        """Durably record that a request has started, before any append is attempted.

        Writing this before ``AuditService.record`` is called is what makes
        recovery possible: if the process dies before the append, restart
        sees a pending row with nothing appended yet and safely retries.
        """

        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO mesh_imports (request_id, canonical_path, status, event_id, sequence) "
                "VALUES (?, ?, ?, NULL, NULL)",
                (request_id, canonical_path_, STATUS_PENDING),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_completed(self, request_id: str, event_id: str, sequence: int) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE mesh_imports SET status = ?, event_id = ?, sequence = ? "
                "WHERE request_id = ?",
                (STATUS_COMPLETED, event_id, sequence, request_id),
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
                CREATE TABLE IF NOT EXISTS mesh_imports (
                    request_id TEXT PRIMARY KEY,
                    canonical_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_id TEXT,
                    sequence INTEGER
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def _find_event_by_request_id(service: AuditService, request_id: str) -> "AuditEvent | None":
    for event in service.query():
        if event.metadata.get(MESH_REQUEST_ID_METADATA_KEY) == request_id:
            return event
    return None


def import_mesh_request(
    ledger: MeshImportLedger, service: AuditService, raw_envelope: "dict[str, Any]"
) -> MeshImportResult:
    """Import one mesh envelope, safely across duplicates, crashes, and restarts.

    A request id is refused (``MeshImportConflictError``) if it was already
    imported for a different canonical path. Otherwise the request id's
    pending state is written *before* any append is attempted, so a crash
    at any point leaves either "nothing recorded yet" or "already recorded"
    -- both of which this function detects and resolves without ever
    appending a duplicate event for the same request id.
    """

    envelope = parse_mesh_envelope(raw_envelope)
    resolved_path = canonical_path(envelope.path)

    existing = ledger.get(envelope.request_id)
    if existing is not None and existing.canonical_path != resolved_path:
        raise MeshImportConflictError(
            f"request {envelope.request_id!r} was previously imported for "
            f"{existing.canonical_path!r}; refusing to reimport it for {resolved_path!r}"
        )

    if existing is None:
        ledger.mark_pending(envelope.request_id, resolved_path)

    recovered = _find_event_by_request_id(service, envelope.request_id)
    if recovered is not None:
        ledger.mark_completed(envelope.request_id, recovered.event_id, recovered.sequence)
        return MeshImportResult(envelope.request_id, resolved_path, recovered, replayed=True)

    event = service.record(
        envelope.actor,
        envelope.action,
        envelope.outcome,
        metadata={**envelope.metadata, MESH_REQUEST_ID_METADATA_KEY: envelope.request_id},
        recorded_at=envelope.recorded_at,
    )
    ledger.mark_completed(envelope.request_id, event.event_id, event.sequence)
    return MeshImportResult(envelope.request_id, resolved_path, event, replayed=False)
