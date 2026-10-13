# Operator runbook: compatibility repair (`POST /v2/integrity`)

No runbook existed for this service before; this is the first one, covering
the compatibility-repair route added for interrupted-import cleanup
(`auditlog/integrity.py`, `SQLiteAuditLogService.repair_duplicates`,
`auditlog/server.py`). It assumes the service is already running via
`python -m auditlog.serve`.

## Running the authenticated repair command

Start the service against the durable store, then call the route with the
configured bearer token:

```text
python -m auditlog.serve --log-store STORE.db --bearer-token TOKEN --host 127.0.0.1 --port 0
```

The first line of output is `PORT <n>`, the actual bound port (useful when
`--port 0` auto-assigns one). Then, from any HTTP client:

```text
curl -s -X POST http://127.0.0.1:<port>/v2/integrity \
  -H "Authorization: Bearer TOKEN"
```

A successful call returns `200` with `{"ok": true, "removed": [...]}`, where
`removed` lists every row that was deleted (empty if there was nothing to
repair). Any request body is ignored outright -- the route never reads it,
so no field in it (including ones named after internal concepts such as
`repair_group` or `archive_ref`) can steer which rows are grouped or which
one survives. A missing or wrong `Authorization` header gets `401` and the
store is left completely untouched; there is no partial-auth or read-only
mode for this route.

## Rollback limits

Repair runs as one SQLite transaction (`BEGIN IMMEDIATE` ... `COMMIT`):

- **Before commit**: fully recoverable. If the process crashes or the
  transaction otherwise fails after the deletes are queued but before
  `COMMIT` runs, nothing was made durable -- reopening the store (a real
  restart, or a fresh connection from any process) shows every row exactly
  as it was before repair was called, including whatever it would have
  removed. Retrying the same repair call afterward is safe and produces the
  same result the original call would have.
- **After commit**: not recoverable. Once a repair call returns `200`, the
  rows listed in `removed` are gone permanently. There is no undo endpoint
  and no soft-delete or tombstone kept anywhere -- this is the one place in
  the service that is allowed to permanently remove rows from the
  otherwise append-only trail, and it is irreversible by design. Take a
  filesystem-level copy of the store file first if you need to be able to
  recover the exact pre-repair state later.
- Repair is idempotent from the caller's side: calling it again immediately
  after a successful call (for example because the response was lost on
  the wire) returns `{"ok": true, "removed": []}` and changes nothing
  further. It is safe to retry on any ambiguous outcome (timeout, dropped
  connection) without risking a second, incorrect removal.

## Separate-process verification

Because the store is a plain SQLite file, you can confirm a repair's result
independently of the serving process, from a second process, without going
through HTTP at all:

```text
python -c "
from auditlog.sqlite_service import SQLiteAuditLogService
service = SQLiteAuditLogService('STORE.db')
for event in service.events():
    print(event.sequence, event.event_id, event.actor, event.recorded_at)
service.close()
"
```

Run this only against a store no other process currently has open for
writing, or after stopping the serving process, to be certain you are
reading the fully-committed result rather than racing an in-progress
transaction. This is the same technique the archived test suite
(`tests/test_integrity_repair_public.py`, `RepairSeparateProcessControlTests`
and `RepairCrashBoundaryTests`) uses to prove repair results are durable and
that a simulated crash before commit leaves the store exactly as it was.

## Known compatibility limits

- **Only exact duplicates are collapsed.** Grouping is keyed on
  `repair_group_key`, which resolves to `recorded_at` + content id
  (`actor`/`action`/`outcome`/`recorded_at`). Two rows only group together
  if every one of those fields matches exactly. The legacy archive format
  described in `README.md` -- which can restamp an event's `at` value
  between exports -- produces rows with a *different* `recorded_at` and
  therefore a different content id and a different repair group; this
  repair pass does not, and is not intended to, collapse those. That
  remains a distinct, unsolved problem from ordinary exact-duplicate
  cleanup.
- **No dry run.** There is no read-only "what would repair remove" mode;
  the only way to see what would be removed is to run it (or reason about
  it externally from `events()` and `repair_group_key`, as the tests do).
- **No CLI access.** `python -m auditlog.cli repair` is still an
  unimplemented stub; compatibility repair is reachable only through
  `POST /v2/integrity` on the loopback HTTP service.
- **Whole-table scan.** `repair_duplicates` loads every row via one
  `SELECT ... FROM events` before deciding what to remove; there is no
  batching or pagination, so its cost scales with total table size, not
  with the number of duplicates actually present.
- **Loopback only.** Like the rest of the HTTP transport, `/v2/integrity`
  is reachable only on `127.0.0.1`/`localhost`; there is no remote or
  authenticated-network-caller story beyond a single shared bearer token.
