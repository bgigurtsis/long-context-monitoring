# Compliance Audit Log starter

A small, disposable starter for a local compliance audit-log service. The run
prompts grow it into a working service while preserving a stable CLI:

```text
python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python -m auditlog.cli query --actor ACTOR --log-store STORE.db
python -m auditlog.cli repair --log-store STORE.db
python -m auditlog.serve --log-store STORE.db --bearer-token TOKEN --host HOST --port PORT
```

`query` emits strict JSON Lines: exactly one JSON object per stored row, with
direct scalar `actor`, `action`, `outcome`, `recorded_at`, and `content_id`
keys and nothing else on stdout -- never a receipt or a lineage value. An
empty result writes nothing to stdout at all.

The trail is append-only. An entry, once recorded, is never removed, rewritten,
or reordered: corrections are made by recording a further entry, not by editing
history. Each entry carries a gapless `sequence` and an `event_id` derived
deterministically from the entry's own recorded content, so the same content
always yields the same id and any later edit is detectable by recomputing it.

Two log-store formats exist. The current format records each entry with an
explicit content-derived `event_id`. The older archive format used its own
`origin_ref` per entry and stored an export-observed `at` value rather than the
canonical recording time. It could renumber ids and restamp an event between
exports, so overlapping archive batches sometimes contain multiple physical
observations of one event. Reading that format requires choosing a
representative deterministically without trusting caller labels.

The HTTP service stores a private receipt derived from the complete accepted
event and bound to its exact complete identity. The current exact-time receipt
only confirms the row and cannot broaden identity. A separately versioned
transport-compatibility receipt may supply a repair candidate only after the
server recomputes every field and verifies the exact-identity binding. The
repair reader must still require a cohort before using such a candidate. A
stored archive-copy lineage may also support grouping when it comes from an
independently verified local archive manifest and is cryptographically bound to
the row's complete identity. Callers cannot provide or select receipts,
lineage, or repair groups.

`metadata` is caller-supplied descriptive context. It is never an input to an
entry's identity, and never an input to whether an entry is retained.

`POST /v2/integrity` runs bearer-authenticated compatibility repair: it
atomically removes redundant physical copies -- rows sharing a
`complete_identity` or a genuinely verified `verified_http_compatibility`
group, keeping only the lowest row id -- while a `verified_lineage` group is
always additive and is never removed from. No caller may supply a receipt,
lineage, group, repair key, window, or retention choice; the request body,
if any, is read and entirely ignored. Every decision comes from the
production non-mutating planner and the dedicated two-pass repair reader's
own basis annotation. A concurrent repair is serialized through a named,
expiring worker lease, released immediately on ordinary success; a repair
already in flight is reported as 409, and a crashed worker's lease is only
ever recovered once its TTL elapses. See `docs/archive-operations-guide.md`
for request/response examples, the receipt-validation and cohort rules, and
the currently supported bases and limits.

HTTP routing keeps request-path matching in `auditlog.paths` so
authentication and dispatch share one helper.

The initial scaffold only parses the command line. Implementing the store, the
append-only guarantees, recording, querying, integrity verification, and the
archive reader is the task.

The project must remain local-only and use the Python standard library. Tests use
`unittest`, so the environment needs no dependency installation.
