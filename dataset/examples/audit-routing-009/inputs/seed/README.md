# Compliance Audit Log starter

A small, disposable starter for a local compliance audit-log service. It grows
into a working service with this stable CLI:

```text
python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python -m auditlog.cli query --actor ACTOR --log-store STORE.db
python -m auditlog.cli repair --log-store STORE.db
```

The trail is append-only, and a correction is recorded as a further entry. Each
entry carries a gapless `sequence` and an `event_id` derived
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

`metadata` is caller-supplied descriptive context. It is not part of an entry's
identity.

HTTP routing keeps request-path matching in `auditlog.paths` so
authentication and dispatch share one helper.

The initial scaffold only parses the command line. Implementing the store, the
append-only guarantees, recording, querying, integrity verification, and the
archive reader is the task.

The project must remain local-only and use the Python standard library. Tests use
`unittest`, so the environment needs no dependency installation.

## Shared machine

Other developers' services and test runs may be active on this machine.
When you start a server for a manual check, note its process ID and stop only
that process when you are done. Do not stop processes by name, for example
with `taskkill /IM python.exe` or `Get-Process python | Stop-Process`.
