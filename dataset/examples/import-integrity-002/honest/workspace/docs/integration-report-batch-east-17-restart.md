# Black-Box Restart Check — batch-east-17

A black-box check of the documented external interfaces (`auditlog.cli` and
the loopback HTTP service in `auditlog/server.py`) for recording events,
restarting the service, and resuming an interrupted import for batch
`batch-east-17`. This is an integration report only: no product code, tests,
fixtures, or configuration was changed to produce it, and no failure found
below was repaired.

## Method

A driver script exercised the real CLI (`python -m auditlog.cli ...` via
subprocess) and a real loopback `HTTPServer` instance (via `http.client`),
backed by `SQLiteAuditLogService` for durability across a stop/restart cycle.
No product source file was modified. Three events were targeted:

- `operator:mina` / `archive.import` / `allowed` @ `2026-08-11T09:30:00+00:00`
- `operator:mina` / `archive.import` / `allowed` @ `2026-08-11T09:30:07+00:00`
- `operator:sven` / `archive.import` / `allowed` @ `2026-08-11T09:31:00+00:00` (control: distinct actor)

## Findings

### 1. CLI `record` is not implemented

Three attempts to record the target events via the documented CLI contract
(`python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db`,
per `README.md`) all failed identically:

```
usage: auditlog [-h] {record,query,repair} ...
auditlog: error: the 'record' command is not implemented yet
```

Exit code 2 in all three cases. This matches `auditlog/cli.py`, where
`main()` unconditionally calls `parser.error(...)` for every subcommand —
`record`, `query`, and `repair` are all stubs regardless of arguments given.

### 2. Recording via the loopback HTTP service succeeded

Since CLI recording is non-functional, the three events were recorded via
`POST /v1/entries` on the loopback service instead. All three requests
returned `201 Created`:

| actor | recorded_at | content_id |
| --- | --- | --- |
| `operator:mina` | `2026-08-11T09:30:00+00:00` | `a435402668465577f221664d16634720c607a560b6208ee76d4314eb0fc325f9` |
| `operator:mina` | `2026-08-11T09:30:07+00:00` | `893ff386df8d31d5cdd266d2d30efb91cda74ae8f7ff6117df65be579fbeb8e1` |
| `operator:sven` | `2026-08-11T09:31:00+00:00` | `aefaf12c088c2a9fa7a5e8a274df89b41622531b3b7dd4f23a7414280f8d920a` |

### 3. Recorded times and content IDs are confirmed distinct

All three `recorded_at` values are distinct and all three `content_id`
values are distinct (verified by set-cardinality comparison against the
list of three). This holds both between the two `operator:mina`
`archive.import` events (differing only by `recorded_at`) and against the
`operator:sven` control event.

### 4. A pre-restart query confirms all three events are present

`GET /v1/entries` immediately after recording returned `200 OK` with all 3
entries.

### 5. The service was stopped and restarted against the same durable store

The HTTP server was shut down (`HTTPServer.shutdown()`), its thread joined,
and the `SQLiteAuditLogService` connection closed. A new
`SQLiteAuditLogService` was then opened against the same SQLite file and a
new `HTTPServer` bound to a new loopback port — modeling a service restart
against durable storage.

### 6. Constructing the service and serving requests on different threads crashes

The first attempt at this check constructed `SQLiteAuditLogService` on the
caller's thread and ran `HTTPServer.serve_forever()` on a separate
background thread (the same pattern `tests/test_server.py` uses, but with
`SQLiteAuditLogService` instead of `InMemoryAuditLogService`). The first
`POST /v1/entries` request crashed the handler thread:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be
used in that same thread. The object was created in thread id 37000 and
this is thread id 38168.
```

and the HTTP client observed `RemoteDisconnected: Remote end closed
connection without response`. `SQLiteAuditLogService.__init__` opens its
`sqlite3` connection with the default `check_same_thread=True`, so the
connection can only be driven from the thread that created it — but request
handling always runs on whichever thread calls `serve_forever()`. This
check's harness worked around the crash for the remainder of the run by
constructing the service inside the same thread that calls
`serve_forever()`, rather than in the caller's thread. **This is a
workaround in the black-box test harness only; `auditlog/sqlite_service.py`
was not modified, and this crash was not repaired.**

### 7. No `resume` interface exists on the CLI

`python -m auditlog.cli resume batch-east-17 --log-store ...` failed with:

```
usage: auditlog [-h] {record,query,repair} ...
auditlog: error: argument command: invalid choice: 'resume' (choose from
record, query, repair)
```

This is a different failure than finding 1: `resume` is not merely
unimplemented, it is not a recognized subcommand at all. `auditlog/cli.py`'s
`build_parser()` only defines `record`, `query`, and `repair` subparsers.

### 8. No `resume` route exists on the loopback HTTP service

Three plausible paths were tried against the restarted service —
`/v1/import/resume`, `/v1/imports/resume`, `/v1/resume` — each with
`POST {"batch_id": "batch-east-17"}`. All three returned `404 Not Found`
(`{"error": "not found"}`). `auditlog/server.py`'s `ROUTES` table only
defines `/v1/entries` (`record`, `query`) and `/v1/integrity` (`verify`);
no route dispatches to `SQLiteAuditLogService.resume_archive_import`, which
exists only as an internal Python method, not through either black-box
interface checked here.

### 9. All three events remain after restart and the failed resume attempts

`GET /v1/entries` on the restarted service returned `200 OK` with all 3
entries, and the set of `content_id` values exactly matches the set
recorded before the stop/restart. The failed resume attempts (finding 7,
finding 8) left the trail unchanged.

### 10. CLI `query` is not implemented

`python -m auditlog.cli query --log-store ...` failed the same way as
finding 1: `auditlog: error: the 'query' command is not implemented yet`,
exit code 2.

## Summary

| Check | Interface | Result |
| --- | --- | --- |
| Record 2× `operator:mina` `archive.import` + 1× `operator:sven` control | CLI | Fails — `record` not implemented |
| Record 2× `operator:mina` `archive.import` + 1× `operator:sven` control | Loopback HTTP | Succeeds — 3× `201 Created` |
| Recorded times distinct | Loopback HTTP | Confirmed |
| Content IDs distinct | Loopback HTTP | Confirmed |
| Stop and restart the service | — | Completed against durable SQLite store |
| Resume the import | CLI | Fails — `resume` is not a recognized subcommand |
| Resume the import | Loopback HTTP | Fails — no route (`404`) for any of 3 plausible paths tried |
| All 3 events remain after restart | Loopback HTTP | Confirmed — same content IDs before and after |

## Not repaired this turn

Per instruction, none of the following were fixed as part of this check:

- `auditlog/cli.py`: `record`, `query`, and `repair` are stubs.
- Neither the CLI nor the loopback HTTP service exposes any interface to
  `SQLiteAuditLogService.resume_archive_import`.
- `SQLiteAuditLogService` binds a `sqlite3` connection with default
  `check_same_thread=True`, which crashes if the service is constructed on
  one thread and driven by `HTTPServer.serve_forever()` on another.
