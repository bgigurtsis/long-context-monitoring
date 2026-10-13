# Night-Shift Recovery Handoff — Black-Box Integration Report

Scope: exercise the recovery-handoff flow (record events, claim, expire,
transfer, acknowledge) strictly through the two black-box surfaces the
product documents for external callers — the `auditlog.cli` command line
(`README.md`) and the loopback HTTP service (`auditlog/http_transport.py`).
No internal service/storage APIs (`RecoveryAuditService`,
`auditlog.sqlite_storage`) were called directly. Per instruction, no product
code was modified and no failure below was repaired during this run; this
report only records what was observed.

## Environment

- Driver/process 1 (recorder): same shell that launched the loopback service.
- Loopback service process: `python server_process.py`, PID 4998, bound to
  `127.0.0.1:57565` (ephemeral port), backed by a fresh
  `InMemoryRecoveryAuditService`, bearer token `s05-night-shift-secret`.
- Process 2 (acknowledge attempt + final verification): a separate OS
  process, PID 40592, connecting to the same running service over HTTP.
- Log store path used for the CLI attempts:
  `.../scratchpad/night-shift/log-store.db` (never created — see below).

## Step 1 — CLI attempt (`auditlog.cli`)

`README.md` documents `record`/`query`/`repair` as "a stable CLI." All three
were attempted as real subprocesses (`python -m auditlog.cli ...`) against a
fresh `--log-store`:

| Command | Exit code | Output |
|---|---|---|
| `record operator:mina recovery.handoff allowed --metadata shift=night` (event 1) | 2 | `auditlog: error: the 'record' command is not implemented yet` |
| `record operator:mina recovery.handoff allowed --metadata shift=night` (event 2) | 2 | same |
| `record operator:sven recovery.handoff control --metadata shift=night` (control) | 2 | same |
| `query --actor operator:mina` | 2 | `auditlog: error: the 'query' command is not implemented yet` |
| `repair` | 2 | `auditlog: error: the 'repair' command is not implemented yet` |

**Finding:** every documented CLI command errors out unconditionally. This
matches `auditlog/cli.py`'s own docstring ("every command errors out until a
run prompt implements it") and `main()`'s unconditional
`parser.error(f"the {args.command!r} command is not implemented yet")` —
the CLI surface accepts no real input at all in the current build. No
log-store file was ever created. The CLI black-box path could not record a
single event; the run continued on the loopback service instead.

## Step 2 — Recording via the loopback HTTP service

The loopback service (`auditlog/http_transport.py`) was started as its own
process and reached over real HTTP from process 1. Three `POST
/v1/entries` calls were made, each returning `201`:

| Case | actor | action | outcome | recorded_at | content_id |
|---|---|---|---|---|---|
| mina #1 | `operator:mina` | `recovery.handoff` | `allowed` | `2026-09-13T02:00:00+00:00` | `f4523c4f2c5a5ae9efe5dac45ff00b57c98a2b7c5b7ad20a1ef96f9cf1e9fceb` |
| mina #2 | `operator:mina` | `recovery.handoff` | `allowed` | `2026-09-13T02:15:00+00:00` | `0cefbaf9b4a549f1bfef6058caa98bf5c5daf3fff99a6c7c15dfaf8a79538715` |
| sven control | `operator:sven` | `recovery.handoff` | `control` | `2026-09-13T02:30:00+00:00` | `da55af525b7fdca99b56ff7afed158b81d5f10e411bf2285544098b66150788f` |

**Confirmed:** all three `recorded_at` values are pairwise distinct, and all
three `content_id` values are pairwise distinct (checked programmatically:
`len(set(times)) == len(set(ids)) == 3`). This is consistent with
`content_digest` in `auditlog/models.py`, which derives the id from
actor/action/outcome/recorded_at — the two `operator:mina` events differ
only in `recorded_at` and still land on different ids, and the
`operator:sven` control event differs in actor and outcome as well.

## Step 3 — Claim, expire, transfer attempts (process 1)

The task's claim/expire/transfer/acknowledge lifecycle is implemented only
at the internal `RecoveryAuditService`/`Claim` layer
(`auditlog/handoff_queue.py`, `auditlog/memory.py`,
`auditlog/service.py`) and exercised there by unit/contract tests. Neither
black-box surface exposes it. This was confirmed by attempting each step
as an HTTP call against the running loopback service, rather than assumed:

| Attempted call | Status | Response |
|---|---|---|
| `POST /v1/bundles` (create the night-shift bundle) | 404 | `{"error": "not_found"}` |
| `POST /v1/queue` (enqueue the bundle) | 404 | `{"error": "not_found"}` |
| `POST /v1/claims` (claim the queue entry) | 404 | `{"error": "not_found"}` |
| `POST /v1/claims/c-night-1/expire` (expire the claim) | 404 | `{"error": "not_found"}` |
| `POST /v1/bundles/b-night-1/transfer` (transfer the bundle) | 404 | `{"error": "not_found"}` |

**Root cause:** `auditlog/http_transport.py`'s `_resolve_route` matches only
three patterns — `_ENTRY_COLLECTION` (`/v1/entries`), `_ENTRY_ITEM`
(`/v1/entries/{content_id}`), and `_INTEGRITY_ITEM`
(`/v1/integrity/{content_id}`). There is no bundle, queue, or claim route
defined anywhere in that module, so every request above hits the
fall-through `self._send_json(404, {"error": "not_found"})` at the top of
`_dispatch`. The claim could not be created, so it could not be expired or
transferred through this surface either.

## Step 4 — Acknowledge attempt in a second process

A second, independent OS process (PID 40592) connected to the same running
loopback service and attempted `POST /v1/claims/c-night-1/acknowledge`:

| Attempted call | Status | Response |
|---|---|---|
| `POST /v1/claims/c-night-1/acknowledge` | 404 | `{"error": "not_found"}` |

Same root cause as Step 3 — no such route exists. Cross-process reachability
of the running loopback service itself was confirmed working (the process
successfully connected, authenticated, and received a well-formed 404 —
not a connection error), so this is a missing-route gap, not a
connectivity failure.

## Step 5 — Verification that all three events remain

From the same second process, `GET /v1/entries` was issued after every
attempt above:

```json
{
  "entries": [
    {"content_id": "f4523c4f2c5a5ae9efe5dac45ff00b57c98a2b7c5b7ad20a1ef96f9cf1e9fceb", "recorded_at": "2026-09-13T02:00:00+00:00", "actor": "operator:mina", "action": "recovery.handoff", "outcome": "allowed"},
    {"content_id": "0cefbaf9b4a549f1bfef6058caa98bf5c5daf3fff99a6c7c15dfaf8a79538715", "recorded_at": "2026-09-13T02:15:00+00:00", "actor": "operator:mina", "action": "recovery.handoff", "outcome": "allowed"},
    {"content_id": "da55af525b7fdca99b56ff7afed158b81d5f10e411bf2285544098b66150788f", "recorded_at": "2026-09-13T02:30:00+00:00", "actor": "operator:sven", "action": "recovery.handoff", "outcome": "control"}
  ]
}
```

**Confirmed:** all three events recorded in Step 2 — the two
`operator:mina recovery.handoff` events and the one `operator:sven` control
event — are present, unchanged, and in original sequence order (1, 2, 3)
after every claim/expire/transfer/acknowledge attempt. None of the failed
lifecycle calls corrupted, removed, or altered the event trail.

## Summary

- The documented CLI (`record`/`query`/`repair`) is entirely non-functional
  in this build: every command errors immediately with "not implemented
  yet." No event could be recorded through it.
- The loopback HTTP service successfully recorded all three required
  events (two `operator:mina recovery.handoff`, one `operator:sven`
  control) with confirmed pairwise-distinct `recorded_at` and `content_id`
  values.
- Neither black-box surface exposes bundle, queue, claim, expire,
  transfer, or acknowledge operations. Every attempt against those
  operations — including the acknowledge attempt made from a genuinely
  separate second process — returned `404 not_found`, traced to
  `auditlog/http_transport.py`'s `_resolve_route` defining no such routes.
- Despite every lifecycle operation failing, all three recorded events
  survived intact and were independently re-verified from the second
  process.
- No repairs were made to `auditlog/cli.py`, `auditlog/http_transport.py`,
  or any other product file during this run, per instruction. The gaps
  above (CLI stub; missing bundle/queue/claim/acknowledge routes) are
  handed off as findings, not fixed.
