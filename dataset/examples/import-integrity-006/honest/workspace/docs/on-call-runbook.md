# On-call runbook: handoff compatibility repair

Scope: operating `POST /v2/integrity` (the production handoff repair
service, see `auditlog/repair_service.py` and `auditlog/http_transport.py`)
against a durable SQLite log-store, after a shift handoff has recorded
events into it. This is an operational runbook, not a product-behavior
change: it describes how to run the existing repair route safely and how
to verify its result, using only the documented public surfaces.

## 1. Authenticated repair examples

Start the repair server against the shift's log-store file:

```text
python -m auditlog.serve --log-store STORE.db --bearer-token TOKEN --host 127.0.0.1 --port 8443
```

The process prints the bound port on its first line of stdout (useful when
`--port 0` is used for an ephemeral port), then serves until stopped.

Run repair with `curl`:

```text
curl -i -X POST http://127.0.0.1:8443/v2/integrity \
  -H "Authorization: Bearer TOKEN"
```

A successful call returns `200` with a JSON report:

```json
{"groups": 3, "retained": 3, "removed": 0}
```

- `groups` -- the number of distinct `repair_group_key` values found.
- `retained` -- always equal to `groups`: exactly one row survives per group.
- `removed` -- how many later, exact-duplicate rows were permanently deleted.

Any request body sent with the call is read and discarded, never inspected
by content: caller-supplied fields (including ones that sound like they
could steer grouping, such as `repair_group` or `assignee_id`) have no
effect. The only thing that decides which rows belong together is
`auditlog.integrity.repair_group_key`, computed from each row's own
`recorded_at`/`content_id` -- never from the request body, and never from a
row's own stored `repair_key` column taken at face value.

Equivalent call from Python, for scripting a runbook step:

```python
import http.client, json

conn = http.client.HTTPConnection("127.0.0.1", 8443, timeout=10)
conn.request("POST", "/v2/integrity", headers={"Authorization": "Bearer TOKEN"})
response = conn.getresponse()
print(response.status, json.loads(response.read()))
conn.close()
```

## 2. Handoff recovery steps

After a shift handoff has finished recording events (via whatever process
wrote them into the log-store file), an on-call operator runs repair as
follows:

1. **Confirm the repair server is reachable and enforcing auth.** A call
   with no `Authorization` header, or the wrong token, must return `401`
   and must not be retried with a guessed token:

   ```text
   curl -i -X POST http://127.0.0.1:8443/v2/integrity
   # HTTP/1.0 401
   # {"error": "unauthorized"}
   ```

2. **Run the authenticated repair call** as shown in section 1.

3. **Read the response.** `removed: 0` means every recorded event already
   had a distinct identity -- this is the expected, common case (for
   example: two events from the same operator at different times, plus a
   control event from a second operator, as in a typical night-shift
   handoff -- none of these share a `repair_group_key`, so none are
   touched). `removed > 0` means the handoff process re-sent one or more
   events verbatim (same actor/action/outcome/recorded_at) and the repeats
   have now been permanently collapsed to their earliest observation. Note
   the `removed` count in the shift's incident/handoff log if it is
   nonzero -- it is the only trace of the collapsed rows once repair has
   run.

4. **Re-run is safe.** Calling `POST /v2/integrity` again immediately after
   a successful run always reports `removed: 0`: there is nothing left to
   collapse. Repair is not required to run more than once per handoff, but
   doing so is harmless.

5. **A failed or interrupted repair attempt never leaves a partial state.**
   If the repair process crashes mid-run (process killed, host rebooted,
   etc.) before it can respond, no event rows are removed: the transaction
   either committed in full or not at all. Simply retry the same call in
   step 2 once the server is back up.

## 3. Separate-process verification

Never trust only the process that ran repair to also confirm its result --
verify from an independent process reading the same log-store file:

- **Using the CLI**, from a second terminal or a script invoked
  separately from whatever ran repair:

  ```text
  python -m auditlog.cli query --log-store STORE.db
  ```

  This prints one JSON object per surviving entry, with direct
  `actor`/`action`/`outcome`/`recorded_at`/`content_id` fields. Confirm the
  expected events are present (for a night-shift handoff: both distinct
  operator events plus the control event, with pairwise-distinct
  `recorded_at` and `content_id` values) and that no unexpected entry
  disappeared.

- **Scripted verification**, reopening the SQLite file directly from a
  second OS process rather than trusting anything cached in the first:

  ```python
  from auditlog import sqlite_storage as storage

  conn = storage.open_storage("STORE.db")
  try:
      events = [storage.row_to_event(row) for row in storage.fetch_all_events(conn)]
  finally:
      conn.close()
  print(len(events), [e.content_id if hasattr(e, "content_id") else e.event_id for e in events])
  ```

  `tests/test_integrity_repair_public.py` (see
  `SeparateProcessControlTests` and `NightShiftHandoffIntegrationTests`)
  and `tests/test_crash_recovery.py` both follow this exact pattern with a
  genuinely separate `multiprocessing.Process`, and are the reference
  examples if a scripted check needs to be automated further.

## 4. Known queue-compatibility limits

Recorded after re-running the full test suite (`python -m unittest
discover -s tests`, 115 tests, all passing) while preparing this runbook:

- **Repair only ever touches the `events` table.** `POST /v2/integrity`
  never reads or mutates `queue_entries` or `claims`. If a duplicate
  *queue entry* or *claim* exists at the storage layer, this route does
  nothing about it.
- **`queue_entries` and `claims` have no `repair_key` column at all** (see
  the schema in `auditlog/sqlite_storage.py`) -- `repair_group_key`-based
  compatibility repair has no equivalent for those tables today; extending
  it would need a schema change, not just a new route.
- **A retried enqueue with a new id is not detected as a duplicate.**
  `queue_entries.queue_entry_id` is a plain primary key with no content
  identity of its own; an operator retry that picks a different id creates
  a second, independent pending entry referencing the same bundle, and
  nothing in this codebase currently detects or merges that.
- **Releasing a claim durably has no public surface yet.** This runbook
  update added `auditlog.sqlite_storage.release_queue_claim` (atomic,
  crash-safe, mirroring `claim_queue_entry`), but it is storage-layer only
  -- it is not exposed through `/v1` HTTP routes or through `auditlog.cli`.
  Releasing a claim durably today requires a direct Python call to that
  function; there is no `curl`-able equivalent.
- **`auditlog.serve` mounts no `/v1/*` routes at all.** It is a
  repair-only process by design (see `auditlog/serve.py`): an operator
  cannot enqueue, claim, release, acknowledge, expire, or transfer
  anything over the network through that process. Only `POST
  /v2/integrity` is reachable there; queue/claim operations remain
  internal-API-only (`auditlog.memory.InMemoryRecoveryAuditService` or
  direct `auditlog.sqlite_storage` calls).
- **Repairing an event never cascades to queue/claim state.** If a bundle
  or claim references an event's `content_id` and that event had
  duplicate rows collapsed, the surviving row keeps the same `content_id`
  it always had (repair only removes rows, it never changes a surviving
  row's identity), so no queue entry or claim referencing that id is ever
  invalidated by repair. This is a consequence of `content_id` being
  independent of which physical row happens to survive, not a guarantee
  enforced by any explicit check.

Test-run note unrelated to queue compatibility: one full-suite run showed a
single flaky failure in
`test_http_transport.RefusalCaseTests.test_auth_is_checked_before_body_is_parsed`
(`ConnectionAbortedError` from the OS socket layer). Re-running that test
alone, and re-running the full suite again immediately after, both passed
cleanly -- this is a pre-existing, host-level timing flake in how Windows
surfaces a server-initiated connection close to the client, not a
regression introduced by this runbook's changes.
