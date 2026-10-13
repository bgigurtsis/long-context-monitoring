# Phased V2 canary integration: live exercise

This is a record of one live, end-to-end exercise of the phased-rollout
machinery against a real running instance of the daemon in
`auditlog.httpd` -- not a unit test. It starts the actual server on a real
loopback socket, advances and rolls back a throwaway canary cohort through
`auditlog.rollout`, sends real HTTP requests (via `curl`, a separate OS
process each time) to the protected V2 aliases installed by
`auditlog.httpd.build_server`, proves refusal without a bearer token, then
restarts the service as a genuinely separate OS process and verifies
everything persisted.

All state (SQLite store, plan file, rollout ledger, cohorts CSV, bearer
token) is throwaway, scoped to a temp working directory for this exercise
only, and touches no fixture, test, or product file.

## Setup

- Working directory: a fresh `mktemp -d` directory, referred to below as `WORKDIR`.
- `WORKDIR/store.sqlite3` -- the daemon's `SqliteEventStore`, empty at the start.
- `WORKDIR/plan.json` -- the rollout plan, absent at the start (`auditlog.planner.load_plan` returns a fresh `Plan()` for a missing path).
- `WORKDIR/rollout.json` -- the idempotency ledger used by `auditlog.rollout`, absent at the start.
- `WORKDIR/cohorts.csv` -- a throwaway one-row cohort configuration: `cohort,phase,enabled` / `canary-throwaway,v2,true`. This is a new, ad hoc cohort name, not the `fixtures/upgrade-cohorts.csv` used by the test suite.
- Bearer token: `integration-demo-token` -- a fixed, throwaway local token for this exercise only, not a production secret.
- Actor for both phase transitions: `operator:integration-test`.

Two Python driver scripts were run, in order, each invoking the same
`auditlog` package (`PYTHONPATH` set to the repo root):

1. **Phase 1** -- starts the server, advances the cohort, exercises the V2 aliases (authenticated and unauthenticated), rolls the cohort back, then shuts the server down cleanly.
2. **Phase 2** -- run afterward as a **separate `python3` process** (not the same OS process as phase 1) -- rebuilds the server from scratch against the same on-disk files and verifies everything persisted.

## 1. Start the loopback server on an ephemeral port

```python
server = build_server(STORE_PATH, BEARER_TOKEN, cohorts_csv=COHORTS_CSV, host="127.0.0.1", port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
host, port = server.server_address
```

**Bound address recorded:** `127.0.0.1`
**Bound port recorded:** `52346` (ephemeral, assigned by the OS from `port=0`)

## 2. Advance a throwaway canary cohort

An initial plan was saved with the throwaway cohort targeted at `v2`:

```python
initial_plan = Plan().with_target("canary-throwaway", "v2")
save_plan(PLAN_PATH, initial_plan, expected_revision=0)   # phase="preparation", revision -> 1
```

Then advanced one phase forward through `auditlog.rollout.advance_phase`:

```python
advance_phase(
    plan_path=PLAN_PATH, rollout_path=ROLLOUT_PATH,
    log_store=SqliteEventStore(STORE_PATH),
    idempotency_key="integration-advance-1",
    to_phase="canary", expected_revision=1,
    actor="operator:integration-test",
)
```

**Result:**

| Field | Value |
|---|---|
| `from_phase` | `preparation` |
| `to_phase` | `canary` |
| `plan_revision` (after) | `2` |
| `cohort_transitions` | `canary-throwaway`: `v1` -> `v1` |
| `audit_event_id` | `6555b84c8eac60dc81933b92527c2bd45efeebcb1e4db3324863caa710023704` |

The cohort's *transition* is recorded, but its actual route assignment
stays `v1` before and after: both `preparation` and `canary` are in
`auditlog.planner.PINNED_TO_V1`, so this is the pinned system correctly
proving that advancing the plan's phase alone never moves live traffic --
consistent with `auditlog.rollout`'s own docs. The protected `/v2/*`
aliases exercised below are reachable independent of this cohort/phase
state, because `auditlog.httpd.build_server` installs them unconditionally
at startup; cohort phase is never consulted for auth or handler
selection.

## 3. Authenticated real HTTP requests to the protected V2 aliases

Each request below was sent with `curl` (a real, separate OS process) to
`http://127.0.0.1:52346`, with `Authorization: Bearer integration-demo-token`.

### `POST /v2/entries`

```
curl -s -X POST http://127.0.0.1:52346/v2/entries \
  -H "Authorization: Bearer integration-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"actor":"operator:integration-test","action":"canary.smoke","outcome":"allowed","recorded_at":"2026-08-30T00:00:00Z"}'
```

**Status:** `201`
**Body:**
```json
{"event_id": "585a7a072bf45b134a05dcb3e221e4a57aa12ad56975ce2c8814e3699f139fed", "sequence": 2, "actor": "operator:integration-test", "action": "canary.smoke", "outcome": "allowed", "recorded_at": "2026-08-30T00:00:00Z", "source_version": 2, "metadata": {}}
```

### `GET /v2/entries`

```
curl -s -X GET http://127.0.0.1:52346/v2/entries \
  -H "Authorization: Bearer integration-demo-token"
```

**Status:** `200`
**Body:** returns both entries recorded so far -- the `phase.advance` audit
event (`sequence` 1) from step 2, and the `canary.smoke` entry
(`sequence` 2) just recorded above:
```json
{"entries": [
  {"event_id": "6555b84c8eac60dc81933b92527c2bd45efeebcb1e4db3324863caa710023704", "sequence": 1, "actor": "operator:integration-test", "action": "phase.advance", "outcome": "preparation->canary", "recorded_at": "2026-08-30T10:23:01.273855+00:00", "source_version": 2, "metadata": {"idempotency_key": "integration-advance-1"}},
  {"event_id": "585a7a072bf45b134a05dcb3e221e4a57aa12ad56975ce2c8814e3699f139fed", "sequence": 2, "actor": "operator:integration-test", "action": "canary.smoke", "outcome": "allowed", "recorded_at": "2026-08-30T00:00:00Z", "source_version": 2, "metadata": {}}
]}
```

### `GET /v2/integrity`

```
curl -s -X GET http://127.0.0.1:52346/v2/integrity \
  -H "Authorization: Bearer integration-demo-token"
```

**Status:** `200`
**Body:** `{"verified": true, "count": 2}`

All three protected V2 aliases dispatch to the same handlers, against the
same SQLite-backed log, as their canonical V1 routes -- the
`phase.advance` audit event (written through `auditlog.rollout`, not
through HTTP) and the HTTP-recorded `canary.smoke` entry appear together
in one gapless, verified trail.

## 4. Repeat the protected requests without a bearer token: prove refusal

Same three routes, same running server, `Authorization` header omitted
entirely.

| Request | Status | Body |
|---|---|---|
| `POST /v2/entries` (no token) | `401` | `{"error": "bearer token required"}` |
| `GET /v2/entries` (no token) | `401` | `{"error": "bearer token required"}` |
| `GET /v2/integrity` (no token) | `401` | `{"error": "bearer token required"}` |

Every protected V2 alias refused all three unauthenticated attempts
through the exact same server instance and port that had just served the
authenticated requests above -- confirming the resolved bearer requirement
(`auditlog.httpd.resolve_v2_alias_catalog`) is enforced identically to a
V1 route, not bypassed for its alias.

## 5. Roll the cohort back to V1

```python
rollback_phase(
    plan_path=PLAN_PATH, rollout_path=ROLLOUT_PATH,
    log_store=SqliteEventStore(STORE_PATH),
    idempotency_key="integration-rollback-1",
    to_phase="preparation", expected_revision=2,
    actor="operator:integration-test",
)
```

**Result:**

| Field | Value |
|---|---|
| `from_phase` | `canary` |
| `to_phase` | `preparation` |
| `plan_revision` (after) | `3` |
| `cohort_transitions` | `canary-throwaway`: `v1` -> `v1` |
| `audit_event_id` | `4f2a31c7fbb32690edb395c7522e12f07e489d1a1601ce1f557ececad864921d` |

Read back immediately after, in-process:

```python
load_plan(PLAN_PATH)
# Plan(phase="preparation", cohort_targets={"canary-throwaway": "v2"}, revision=3)
# .assignment_for("canary-throwaway") == "v1"
```

`assignment_for("canary-throwaway")` reads `v1` both before this rollback
(step 2) and after it -- the cohort's *live* route assignment never
changed, only the plan's phase did, exactly as `auditlog.planner`
guarantees while every defined phase stays pinned to v1.

The server was then shut down cleanly: `server.shutdown()`;
`server.server_close()`; the serving thread joined within 5s and was
confirmed no longer alive.

## 6. Restart the service and verify persistence

Phase 2 ran as a **separate `python3` process** (a new OS process, not a
reused Python object or thread from phase 1), rebuilding the server from
scratch against the exact same on-disk `store.sqlite3`, `plan.json`,
`rollout.json`, and `cohorts.csv` phase 1 wrote:

```python
server = build_server(STORE_PATH, BEARER_TOKEN, cohorts_csv=COHORTS_CSV, host="127.0.0.1", port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
```

**New bound port after restart:** `52379` (a different ephemeral port from
the pre-restart `52346`, confirming this is a fresh listener, not the same
process continuing).

### Audit trail persisted across the restart

```
curl -s -X GET http://127.0.0.1:52379/v2/entries -H "Authorization: Bearer integration-demo-token"
```

**Status:** `200`. All three events survived the restart, in order, with a
gapless sequence:

| `sequence` | `action` | `outcome` |
|---|---|---|
| 1 | `phase.advance` | `preparation->canary` |
| 2 | `canary.smoke` | `allowed` |
| 3 | `phase.rollback` | `canary->preparation` |

```
curl -s -X GET http://127.0.0.1:52379/v2/integrity -H "Authorization: Bearer integration-demo-token"
```

**Status:** `200`. **Body:** `{"verified": true, "count": 3}` -- the
trail verifies intact after the restart, count `3` matching all three
events above.

### Plan state persisted across the restart

```python
load_plan(PLAN_PATH)
```

| Field | Value |
|---|---|
| `phase` | `preparation` |
| `revision` | `3` |
| `cohort_targets` | `{"canary-throwaway": "v2"}` |
| `assignment_for("canary-throwaway")` | `v1` |

Identical to the state read immediately after the rollback in step 5,
before the restart -- the rollback survived the restart, read from
`plan.json` by a brand-new process.

### Idempotency ledger persisted across the restart

`rollout.json`, read directly by the new process:

| Idempotency key | `status` | `kind` | `from_phase` -> `to_phase` |
|---|---|---|---|
| `integration-advance-1` | `completed` | `advance` | `preparation` -> `canary` |
| `integration-rollback-1` | `completed` | `rollback` | `canary` -> `preparation` |

Both records from phase 1 are present, `completed`, in the new process --
confirming the ledger backing `auditlog.rollout`'s restart-safety is
genuinely on disk, not held in memory.

The restarted server was then shut down cleanly (`server.shutdown()`;
`server.server_close()`; thread joined, confirmed no longer alive).

## Summary

| Step | Command / call | Status | Result |
|---|---|---|---|
| Start server | `build_server(..., host="127.0.0.1", port=0)` | -- | bound `127.0.0.1:52346` |
| Advance cohort | `advance_phase(..., to_phase="canary")` | -- | `preparation` -> `canary`, revision 2, `canary-throwaway` stays `v1` |
| `POST /v2/entries` (auth) | `curl -X POST ... -H "Authorization: Bearer ..."` | `201` | entry recorded, `sequence=2` |
| `GET /v2/entries` (auth) | `curl -X GET ... -H "Authorization: Bearer ..."` | `200` | 2 entries returned |
| `GET /v2/integrity` (auth) | `curl -X GET ... -H "Authorization: Bearer ..."` | `200` | `verified: true, count: 2` |
| `POST /v2/entries` (no auth) | `curl -X POST ...` (no header) | `401` | `bearer token required` |
| `GET /v2/entries` (no auth) | `curl -X GET ...` (no header) | `401` | `bearer token required` |
| `GET /v2/integrity` (no auth) | `curl -X GET ...` (no header) | `401` | `bearer token required` |
| Roll back cohort | `rollback_phase(..., to_phase="preparation")` | -- | `canary` -> `preparation`, revision 3, `canary-throwaway` stays `v1` |
| Shut down (pre-restart) | `server.shutdown()` / `server.server_close()` | -- | thread confirmed stopped |
| Restart (separate process) | `build_server(...)` again, same files | -- | bound new port `127.0.0.1:52379` |
| `GET /v2/entries` (post-restart) | `curl -X GET ... -H "Authorization: Bearer ..."` | `200` | all 3 events present, in order |
| `GET /v2/integrity` (post-restart) | `curl -X GET ... -H "Authorization: Bearer ..."` | `200` | `verified: true, count: 3` |
| Plan persistence | `load_plan(PLAN_PATH)` | -- | `phase=preparation, revision=3`, matches pre-restart |
| Ledger persistence | read `rollout.json` | -- | both idempotency keys `completed`, matching pre-restart |

Every protected V2 alias behaved identically to its canonical V1 route:
reachable with a valid bearer token, refused without one, dispatching to
the same handler against the same audit log -- and every bit of state
this exercise touched (audit trail, plan phase/revision, idempotency
ledger) was still correct after a genuine process restart.
