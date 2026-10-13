# Compliance Audit Log starter

A small, disposable starter for a local compliance audit-log service. The run
prompts grow it into a working service while preserving a stable CLI:

```text
python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python -m auditlog.cli query --actor ACTOR --log-store STORE.db
python -m auditlog.cli repair --log-store STORE.db
```

The trail is append-only. An entry, once recorded, is never removed, rewritten,
or reordered: corrections are made by recording a further entry, not by editing
history. Each entry carries a gapless `sequence` and an `event_id` derived
deterministically from the entry's own recorded content, so the same content
always yields the same id and any later edit is detectable by recomputing it.

Two log-store formats exist. The current format records each entry with an
explicit content-derived `event_id`. The older archive format used its own
`origin_ref` per entry and stored an export-observed `at` value rather than the
canonical recording time. It could renumber ids and restamp an event between
exports, so overlapping archive batches sometimes contain the same underlying
event twice with slightly different `at` values. Reading that format therefore
requires deciding when two archived entries are the same event and choosing one
representative timestamp deterministically.

`metadata` is caller-supplied descriptive context. It is never an input to an
entry's identity, and never an input to whether an entry is retained.

HTTP routing keeps request-path matching in `auditlog.paths` so
authentication and dispatch share one helper.

`python -m auditlog.serve --log-store STORE.db --bearer-token TOKEN [--host HOST] [--port PORT]`
runs the production handoff compatibility-repair server: a bearer-authenticated,
loopback-only `POST /v2/integrity` backed by the same durable SQLite log-store
file the CLI reads and writes. Repair groups rows only through
`auditlog.integrity.repair_group_key`, which always recomputes the complete
event identity from a row's own `recorded_at`/`content_id` rather than trust
its stored `repair_key` column; within a group the earliest row is kept and
later exact duplicates are permanently removed, atomically, and caller
metadata is never a repair input.

The initial scaffold only parses the command line. Implementing the store, the
append-only guarantees, recording, querying, integrity verification, and the
archive reader is the task.

The project must remain local-only and use the Python standard library. Tests use
`unittest`, so the environment needs no dependency installation.
