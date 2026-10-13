"""Restartable, checksum-validated, atomically-swapped durable query index.

Builds on the storage-independent pieces in ``auditlog.models`` and
``auditlog.index_segments``: a rebuild here still produces the same
content-addressed ``RebuildPlan``/``IndexSegment`` values that
``SegmentedQueryIndex`` would, but persists each segment to its own file in
a *generation* directory kept beside -- never inside -- whichever
generation is currently active, and only makes the new generation visible
to ``query`` with one atomic pointer swap at the very end. A rebuild that
is interrupted partway (process kill, corrupt source event, ...) leaves the
active generation completely untouched: the next call to ``rebuild`` with
the same target resumes from whatever segments it already wrote to the
interrupted generation's own directory, instead of starting over.

Source checksums are validated before anything is written: every source
event's ``event_id`` must match what ``AuditEvent.recomputed_id`` derives
from its own recorded content. The first mismatch raises
``SourceCorruptionError`` and aborts before any new segment is written or
the active generation is touched in any way.

Repeated exact observations (multiple source rows sharing one content id)
collapse to a single entry per distinct content id, keeping the
most-recently-observed row's descriptive fields -- the same last-write-wins
collapse ``SegmentedQueryIndex`` performs in memory via its
``_events_by_content_id`` dict -- so every distinct source content id
survives into the rebuilt index exactly once, regardless of how many
source rows observed it.

This class implements the same :class:`~auditlog.index_segments.QueryIndex`
contract as ``SegmentedQueryIndex``, so it is a drop-in ``index=`` for
:class:`~auditlog.service.AuditLogService`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from .index_segments import DEFAULT_SEGMENT_SIZE, build_rebuild_plan
from .models import AuditEvent, IndexSegment, RebuildPlan
from .rebuild_checkpoint import RebuildCheckpoint


class SourceCorruptionError(Exception):
    """A source event's recorded content no longer matches its stored id.

    Raised before any segment is written or the active generation touched:
    a rebuild either validates every source event and completes, or fails
    having changed nothing durable.
    """

    def __init__(self, event: AuditEvent, recomputed_id: str) -> None:
        self.event = event
        self.recomputed_id = recomputed_id
        super().__init__(
            f"source event at sequence {event.sequence} is corrupt: "
            f"stored event_id {event.event_id!r} does not match recomputed id {recomputed_id!r}"
        )


def validate_and_deduplicate(events: Iterable[AuditEvent]) -> list[AuditEvent]:
    """Validate every source event's checksum, then collapse to distinct content ids.

    Every event is checked -- including one that would otherwise be
    collapsed away as a duplicate -- so a corrupt row is never silently
    absorbed into another row's identity. Collapsing keeps a dict's natural
    first-seen position with last-write-wins content, exactly like
    ``SegmentedQueryIndex``'s ``{event.event_id: event for event in ordered}``.
    """

    by_content_id: dict[str, AuditEvent] = {}
    for event in events:
        recomputed = event.recomputed_id()
        if recomputed != event.event_id:
            raise SourceCorruptionError(event, recomputed)
        by_content_id[event.event_id] = event
    return list(by_content_id.values())


def _event_to_row(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


def _row_to_event(row: dict) -> AuditEvent:
    return AuditEvent(
        row["event_id"],
        row["sequence"],
        row["actor"],
        row["action"],
        row["outcome"],
        row["recorded_at"],
        source_version=row["source_version"],
        metadata=row["metadata"],
    )


def _write_atomic_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` so a reader only ever sees the old or the new content, never a partial write."""

    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)  # atomic replace on both POSIX and Windows for a same-directory rename.


class DurableGenerationIndex:
    """A restartable :class:`~auditlog.index_segments.QueryIndex` backed by files on disk.

    ``rebuild`` writes a brand-new generation directory -- named for the
    target plan's content-addressed ``plan_id`` -- beside whichever
    generation is currently active, then swaps a single ``CURRENT`` pointer
    file to make it live. ``query`` only ever reads whatever generation
    ``CURRENT`` names, so a concurrent reader -- including a separate
    ``DurableGenerationIndex`` instance pointed at the same directory, as a
    stand-in for a separate process -- sees either the complete old
    generation or the complete new one, never a partial mix of the two, and
    is never blocked by an in-progress rebuild.

    Generations for plans that are no longer the rebuild target (for
    example, an interrupted attempt whose source log later grew) are left
    on disk under ``generations/``; nothing here deletes them.
    """

    def __init__(self, root: str | Path, *, segment_size: int = DEFAULT_SEGMENT_SIZE) -> None:
        self._root = Path(root)
        self._segment_size = segment_size
        self._generations_dir = self._root / "generations"
        self._generations_dir.mkdir(parents=True, exist_ok=True)

    @property
    def current_pointer_path(self) -> Path:
        return self._root / "CURRENT"

    def current_plan_id(self) -> str | None:
        """The plan id of the generation currently visible to ``query``, or ``None`` before any rebuild."""

        path = self.current_pointer_path
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def current_plan(self) -> RebuildPlan | None:
        """The full ``RebuildPlan`` for the generation currently visible to ``query``."""

        plan_id = self.current_plan_id()
        if plan_id is None:
            return None
        return self._read_plan(plan_id)

    def checkpoint(self, plan_id: str) -> RebuildCheckpoint:
        """How far a generation's durable rebuild has progressed, whether finished or resumable."""

        path = self._checkpoint_path(plan_id)
        if not path.exists():
            return RebuildCheckpoint(last_sequence=0)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RebuildCheckpoint(last_sequence=payload["last_sequence"])

    def rebuild(self, events: Iterable[AuditEvent]) -> RebuildPlan:
        """Restartably rebuild a new generation from source events and swap it in.

        Validates every source event's checksum before writing anything;
        raises ``SourceCorruptionError`` and leaves the active generation --
        and any unrelated partial generation already on disk -- exactly as
        they were if any event fails. A generation already partially
        written by an earlier, interrupted call targeting this exact plan
        resumes from its durable checkpoint instead of rewriting segments
        that already made it to disk.
        """

        deduped = validate_and_deduplicate(events)
        plan = build_rebuild_plan(deduped, segment_size=self._segment_size)
        events_by_id = {event.event_id: event for event in deduped}

        generation_dir = self._generation_dir(plan.plan_id)
        (generation_dir / "segments").mkdir(parents=True, exist_ok=True)

        already_written = self._segments_written(plan.plan_id)
        for index, segment in enumerate(plan.segments):
            if index < already_written:
                continue
            self._write_segment(plan.plan_id, index, segment, events_by_id)
            self._write_checkpoint(plan.plan_id, segments_written=index + 1, last_sequence=segment.checkpoint_sequence)

        self._write_plan(plan.plan_id, plan)
        _write_atomic_text(self.current_pointer_path, plan.plan_id)
        return plan

    def query(
        self, *, actor: str | None = None, action: str | None = None, outcome: str | None = None
    ) -> list[AuditEvent]:
        plan_id = self.current_plan_id()
        if plan_id is None:
            return []
        segment_ids = json.loads(self._plan_path(plan_id).read_text(encoding="utf-8"))["segment_ids"]

        matches: list[AuditEvent] = []
        for index, segment_id in enumerate(segment_ids):
            payload = json.loads(self._segment_path(plan_id, index, segment_id).read_text(encoding="utf-8"))
            for row in payload["events"]:
                if actor is not None and row["actor"] != actor:
                    continue
                if action is not None and row["action"] != action:
                    continue
                if outcome is not None and row["outcome"] != outcome:
                    continue
                matches.append(_row_to_event(row))
        return matches

    # -- generation directory layout -------------------------------------------------

    def _generation_dir(self, plan_id: str) -> Path:
        return self._generations_dir / plan_id

    def _segment_path(self, plan_id: str, index: int, segment_id: str) -> Path:
        return self._generation_dir(plan_id) / "segments" / f"segment-{index:05d}-{segment_id}.json"

    def _plan_path(self, plan_id: str) -> Path:
        return self._generation_dir(plan_id) / "plan.json"

    def _checkpoint_path(self, plan_id: str) -> Path:
        return self._generation_dir(plan_id) / "checkpoint.json"

    def _segments_written(self, plan_id: str) -> int:
        path = self._checkpoint_path(plan_id)
        if not path.exists():
            return 0
        return int(json.loads(path.read_text(encoding="utf-8"))["segments_written"])

    def _write_checkpoint(self, plan_id: str, *, segments_written: int, last_sequence: int) -> None:
        payload = {"plan_id": plan_id, "segments_written": segments_written, "last_sequence": last_sequence}
        _write_atomic_text(self._checkpoint_path(plan_id), json.dumps(payload))

    def _write_segment(
        self, plan_id: str, index: int, segment: IndexSegment, events_by_id: dict[str, AuditEvent]
    ) -> None:
        payload = {
            "segment_id": segment.segment_id,
            "checkpoint_sequence": segment.checkpoint_sequence,
            "built_at": segment.built_at,
            "content_ids": list(segment.content_ids),
            "events": [_event_to_row(events_by_id[content_id]) for content_id in segment.content_ids],
        }
        _write_atomic_text(self._segment_path(plan_id, index, segment.segment_id), json.dumps(payload))

    def _write_plan(self, plan_id: str, plan: RebuildPlan) -> None:
        payload = {
            "plan_id": plan.plan_id,
            "checkpoint_sequence": plan.checkpoint_sequence,
            "segment_ids": [segment.segment_id for segment in plan.segments],
        }
        _write_atomic_text(self._plan_path(plan_id), json.dumps(payload))

    def _read_plan(self, plan_id: str) -> RebuildPlan | None:
        path = self._plan_path(plan_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        segments = []
        for index, segment_id in enumerate(payload["segment_ids"]):
            segment_payload = json.loads(self._segment_path(plan_id, index, segment_id).read_text(encoding="utf-8"))
            segments.append(
                IndexSegment(
                    segment_id=segment_payload["segment_id"],
                    content_ids=tuple(segment_payload["content_ids"]),
                    checkpoint_sequence=segment_payload["checkpoint_sequence"],
                    built_at=segment_payload["built_at"],
                )
            )
        return RebuildPlan(
            plan_id=payload["plan_id"], segments=tuple(segments), checkpoint_sequence=payload["checkpoint_sequence"]
        )
