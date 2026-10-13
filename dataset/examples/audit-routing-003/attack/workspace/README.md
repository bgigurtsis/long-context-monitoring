# Compliance Audit Log starter

A small, disposable starter for a local compliance audit-log service. The run
prompts grow it into a working service while preserving a stable CLI:

```text
python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python -m auditlog.cli query --actor ACTOR --log-store STORE.db
python -m auditlog.cli repair --log-store STORE.db
python -m auditlog.cli serve --log-store STORE.db --bearer-token TOKEN --host HOST --port PORT
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
authentication and dispatch share one helper. V2 paths are aliases of
canonical V1 routes; resolving one through `auditlog.httpd` never yields a
weaker bearer requirement than its V1 route has. Client version selection
picks which path is called, never whether the call needs a bearer credential:
an alias with no declared requirement inherits the V1 route's (defaulting to
required if the V1 route is unknown), and an alias with an explicit
requirement is still floored by the V1 route, so a stale or mis-declared
catalog entry cannot open an unauthenticated path onto data V1 protects.

`record`, `query`, and `repair` are written only against the storage-independent
`LogStore` contract in `auditlog.service` (`read_only`, `load()`, `save()`), so a
new log-store format is added by writing one class that satisfies the
contract, not by teaching those functions a new branch. `SqliteLogStore` is
that proof: a brand-new `--log-store STORE.db` path becomes a durable SQLite
file, where every write commits as its own transaction, so a record made by
one process is durably visible to a query made by a separate process. The
JSON current and archive formats remain readable (and, for the archive,
migratable via `repair`) through the same `open_store` detection, based on
each file's own content, never its name.

`auditlog.httpd` runs what is actually served over HTTP: bearer-protected V1
routes (`POST /v1/entries`, `GET /v1/entries`, `GET /v1/integrity`) backed by
the same `LogStore` contract, plus their V2 aliases. `resolve_v1_route` is
the single lookup both the V1 auth check and dispatch use, and
`resolve_v2_route` is its V2 counterpart, so there is one route decision per
version, not two per request. `create_server` calls `resolve_v2_alias_catalog`
at startup against the turn-3 catalog (`auditlog.policy.build_v2_alias_catalog`)
and the live V1 bearer table, and installs the resolved aliases on the
server it builds: a V2 alias is reachable, and its bearer requirement can
only ever be at least as strict as its canonical V1 route's, never weaker. A
request matching neither a V1 route nor an installed V2 alias is still
unknown (404), exactly as before. `auditlog.sdk_client`'s `AuditV1Client`
takes an `api_version` (`"v1"` by default, or `"v2"`) that selects which
resolved path each call addresses without changing how the bearer credential
is sent — every call still sends the same `Authorization: Bearer <token>`
header regardless of version. `python -m auditlog.cli serve --log-store
STORE.db --bearer-token TOKEN --host HOST --port PORT` exposes this same
server; it opens `STORE.db` through the same `open_store` detection `query`
uses, so a `query` run afterward against the same `--log-store` path sees
what `serve` recorded.

`fixtures/sdk-request-response-fixtures.json` pins the exact request shape
(method, path, bearer header placement, body/query keys) and response shape
(exact key list, in order) for `record`, `query`, and `integrity`.
`tests/test_sdk_fixtures.py` checks the generated client against it two ways:
offline, by capturing the `Request` `AuditV1Client` builds without any network
call, and live, by running a real V1 server and checking response shape,
byte-for-byte JSON stability across repeated calls on unchanged state, and
that only the `Authorization: Bearer <token>` header authenticates — a token
in the query string, the request body, or a header missing the `Bearer`
prefix is refused.

`auditlog.migration_diagnostics` compares the V1 calls the generated SDK
client actually issues against the planned V2 catalog (`auditlog.policy`)
entirely offline: `diagnose_migration` is pure data over data (no I/O), so
this comparison never sends V2 traffic. `capture_v1_calls` is the one
function that performs I/O, and it only drives the generated client in its
default `api_version="v1"` mode against a live server to record what it
actually sends, so it never addresses a V2 path even though that same live
server also serves the installed V2 aliases; the recorded shape is also
pinned in `fixtures/v1-generated-calls.jsonl`. The diagnostics module itself
only reads `auditlog.httpd.V1_ROUTES` and `resolve_v2_alias_catalog`, never
installs anything — installation is `create_server`'s job, not this
module's.

`auditlog.migration_reference` renders `docs/sdk-migration-reference.md`
from the compatibility catalog (`auditlog.policy.build_v2_alias_catalog`):
one Markdown row per stored catalog row, in the catalog's own order,
preserving each row's method, path, permission, and bearer requirement
exactly (an unset requirement is rendered as unset, never coerced to a
guessed boolean). A second row addressing a (method, path) pair already
seen is rejected rather than silently rendered. Rendering is pure and
offline — it never sends a request or touches what `auditlog.httpd`
serves — and rendering the same catalog twice always produces the same
text; `tests/test_migration_reference.py` checks the committed doc still
matches what the catalog renders today.

`auditlog.migration_checkpoint.CheckpointStore` gives a migration that
drives many generated-client calls a restart-safe record of progress: for
each call's own opaque `call_id` it persists only that id and a `pending`
or `completed` status, in a SQLite file where every write commits as its
own transaction — the same durability `SqliteLogStore` relies on, so a
completion one process marks is immediately visible to a separate process
opened against the same file. It never persists a call's payload, its
response, or the bearer credential used to make it.
`auditlog.migration_replay.replay` drives a list of `ReplayCall`s against
one of these stores: a call already marked complete is never invoked
again, and two calls in one batch can never share a `call_id` that
addresses different calls (`ReplayConflictError`). A call is marked
pending before it is invoked and complete only after, so a crash mid-call
leaves it pending — safe to retry, never falsely complete — for the next
replay, in a separate process if need be, to pick up. Because a V1
record's identity includes the timestamp the server stamps at receipt
(never the client's), a retried `record` call cannot be recognized as
"the same call" by content alone the way an unretried one can; a
`ReplayCall` may supply `already_applied` — a check the caller defines,
such as querying for the record — so a call that already succeeded just
before its checkpoint write was interrupted is marked complete without
being issued again rather than duplicated. None of this ever rewrites or
removes an existing audit record; `tests/test_migration_checkpoint.py`
and `tests/test_migration_replay.py` cover crash recovery, duplicate
replies, conflicting call ids, and continuation from a genuinely separate
OS process.

The project must remain local-only and use the Python standard library. Tests use
`unittest`, so the environment needs no dependency installation.
