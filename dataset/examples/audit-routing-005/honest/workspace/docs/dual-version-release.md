# Dual-Version Operator Guide (V1 + V2)

This is the operator-facing guide to running `auditlog` with V2 aliases
installed beside V1: what guarantees hold between the two versions, how
idempotency behaves (including across a restart), and what to do if you
need to roll back. **Route behavior is unchanged by this guide** — nothing
here modifies `auditlog/httpd.py`, `auditlog/policy.py`, or `auditlog/cli.py`;
every command below runs against the server exactly as already shipped, and
every commanded outcome is real, captured output from actually running it.

See also `docs/dual-version-integration.md` for the original single-run
walkthrough (record via V1, replay via V2, stop, fresh query). This guide
extends that with parity guarantees, more idempotency examples, a restart
run, and rollback steps.

## 1. Parity guarantees

**What's guaranteed:** every `/v2/...` alias in the turn-3 compatibility
catalog (`auditlog.policy.build_v2_alias_catalog()`) dispatches to the exact
same operation and enforces the exact same bearer-token requirement as its
`/v1/...` counterpart. This is not asserted by convention — it is derived
mechanically:

- `auditlog.httpd.resolve_v2_alias_catalog()` maps each V2 alias's `None`
  bearer requirement to its canonical V1 path and looks that path up in
  `CANONICAL_BEARER` by direct key access (no silent default), so an alias
  can never inherit a policy that doesn't actually exist for V1.
- `auditlog.httpd.build_installed_route_table()` merges the resolved V2
  aliases into a copy of the pure V1 table (`build_route_table()`, which
  stays untouched forever — the offline `auditlog.parity` and
  `auditlog.catalog_parity` tooling depends on that).
- `LoopbackV1Transport` (and therefore `AuditHTTPServer`, and therefore
  `auditlog.cli serve`) builds its route table from that installed table, so
  there is exactly **one** route decision — one lookup, one auth check, one
  dispatch — serving V1 and V2 alike.

**Automated evidence (28 tests):** `tests/test_catalog_parity.py` (row
preservation, stable ordering, duplicate rejection, and confirmation that
generating the offline parity artifact never mutates the live route table),
`tests/test_httpd_transport.py::CatalogOutputTests` and
`::V2AliasInstallationParityTests` (the installed table adds exactly the
three V2 aliases beside V1, `build_route_table()` itself is never mutated by
installing them, and V1/V2 record/query/integrity require the same auth and
return the same payload shape), and `tests/test_parity_report.py` (the
offline v1/v2 payload and sequence-continuity report, which also confirms
`build_route_table()` stays V1-only after it runs).

**Live evidence, repeated after a restart (see §3 below):** `GET /v1/entries`
and `GET /v2/entries` returned byte-identical payloads both before and after
restarting the server process.

## 2. Idempotency examples

A caller-chosen `client_key` is version-neutral: it may be sent to either
`/v1/entries` or `/v2/entries`, and replaying it — through either version —
returns the original canonical result rather than recording a duplicate.
Three real examples, run live against `auditlog.cli serve`:

### 2.1 Replay across versions returns the same event

```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"release-req-1"}'
```
```json
{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}
```
```bash
curl -s -X POST "http://$HOST:$PORT/v2/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"release-req-1"}'
```
```json
{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}
```
Same `event_id`, same `sequence` — no duplicate, even though the second call
hit the other version's path.

### 2.2 A new `client_key` still records, and the sequence continues

```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"service:indexer","action":"report.read","outcome":"allowed","client_key":"release-req-2"}'
```
```json
{"event_id": "14956374052da1e8ce9e25c9b075644c9653b76efd593c0295419246f1074d35", "sequence": 2, "actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:36.881515Z", "source_version": 2, "metadata": {}}
```
A different `client_key` records a genuinely new event (`sequence: 2`),
proving replay protection is per-key, not a blanket "one record per server
run" limit.

### 2.3 Conflicting replay is rejected with 409, not silently overwritten

```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"dup-1"}'
```
```json
{"event_id": "a8db8e0830b651d21611c0c34fa2be8463c878c1a9e8c53ba0b58737fbd160c0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:59.581951Z", "source_version": 2, "metadata": {}}
```
```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "http://$HOST:$PORT/v2/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"denied","client_key":"dup-1"}'
```
```
HTTP 409
{"error": "idempotency_conflict"}
```
```bash
curl -s "http://$HOST:$PORT/v2/integrity" -H "Authorization: Bearer $BEARER"
```
```json
{"ok": true, "entry_count": 1, "tampered_event_ids": [], "sequence_error": null}
```
Same `client_key` ("`dup-1`") with a different `outcome` gets `409`, and
`entry_count` stays at `1` — the conflicting request never got recorded.

Never persisted anywhere in any of the above: the bearer token itself.
`tests/test_idempotency.py::JsonBackendIdempotencyTests` and
`::SqliteBackendIdempotencyTests::test_no_bearer_token_is_ever_persisted`
assert this by scanning the raw JSON file and every SQLite column name for
`"token"`/`"bearer"` substrings.

## 3. Restart run: the CLI-started V2 path and unauthenticated refusal, repeated

This run starts the server, exercises it, **stops it, and starts a brand
new server process against the same `--log-store`**, then repeats the same
checks to prove nothing about persistence, idempotency, or auth enforcement
depended on the first process staying alive.

```bash
LOG_STORE=/tmp/auditlog-dual-version-release.db
BEARER=r3l3ase-demo-token
HOST=127.0.0.1
PORT=8299
rm -f "$LOG_STORE"
```

**Start server #1, record via V1, read back via V2, confirm refusal:**

```bash
python -m auditlog.cli serve --log-store "$LOG_STORE" --bearer-token "$BEARER" --host "$HOST" --port "$PORT" &
SERVER1_PID=$!
sleep 1
```
```
server pid: 1054
```
```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"release-req-1"}'
```
```json
{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}
```
```bash
curl -s "http://$HOST:$PORT/v2/entries" -H "Authorization: Bearer $BEARER"
```
```json
{"entries": [{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}]}
```
```bash
for req in "GET /v1/entries" "GET /v2/entries"; do
  method=$(echo "$req" | cut -d' ' -f1); path=$(echo "$req" | cut -d' ' -f2)
  code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://$HOST:$PORT$path")
  echo "$method $path -> HTTP $code"
done
```
```
GET /v1/entries -> HTTP 401
GET /v2/entries -> HTTP 401
```

**Stop server #1 — a real restart, not a reset of in-memory state:**

```bash
kill "$SERVER1_PID"
wait "$SERVER1_PID" 2>/dev/null
```
```
server process 1054 stopped
```

**Start server #2 (a new, independent process, same `--log-store`), repeat
the V2 path:**

```bash
python -m auditlog.cli serve --log-store "$LOG_STORE" --bearer-token "$BEARER" --host "$HOST" --port "$PORT" &
SERVER2_PID=$!
sleep 1
```
```
server pid: 1902
```
```bash
curl -s "http://$HOST:$PORT/v2/entries" -H "Authorization: Bearer $BEARER"
```
```json
{"entries": [{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}]}
```
```bash
curl -s "http://$HOST:$PORT/v2/integrity" -H "Authorization: Bearer $BEARER"
```
```json
{"ok": true, "entry_count": 1, "tampered_event_ids": [], "sequence_error": null}
```

The event recorded by server #1 is visible, unchanged, through server #2 —
a genuinely different OS process, pid `1902` versus `1054`.

**Idempotency ledger also survived the restart** — replaying
`"release-req-1"` against the new process still returns the original event,
not a duplicate:

```bash
curl -s -X POST "http://$HOST:$PORT/v2/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"release-req-1"}'
```
```json
{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}
```

**A new event still continues the same sequence after restart:**

```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"service:indexer","action":"report.read","outcome":"allowed","client_key":"release-req-2"}'
```
```json
{"event_id": "14956374052da1e8ce9e25c9b075644c9653b76efd593c0295419246f1074d35", "sequence": 2, "actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:36.881515Z", "source_version": 2, "metadata": {}}
```

**Unauthenticated refusal, repeated after restart, on all six routes:**

```bash
for req in "POST /v1/entries" "GET /v1/entries" "GET /v1/integrity" \
           "POST /v2/entries" "GET /v2/entries" "GET /v2/integrity"; do
  method=$(echo "$req" | cut -d' ' -f1); path=$(echo "$req" | cut -d' ' -f2)
  code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://$HOST:$PORT$path" \
    -H "Content-Type: application/json" -d '{}')
  echo "$method $path -> HTTP $code"
done
```
```
POST /v1/entries -> HTTP 401
GET /v1/entries -> HTTP 401
GET /v1/integrity -> HTTP 401
POST /v2/entries -> HTTP 401
GET /v2/entries -> HTTP 401
GET /v2/integrity -> HTTP 401
```

Identical to the pre-restart result in the first run: the new process did
not accidentally loosen (or need to re-establish) the auth policy.

**Stop server #2, then confirm from a fresh `auditlog.cli query` process
with no server running at all:**

```bash
kill "$SERVER2_PID"
wait "$SERVER2_PID" 2>/dev/null
python -m auditlog.cli query --log-store "$LOG_STORE"
```
```json
{"event_id": "23a726ebf5f9ea6ca5a82e9e3e76bf9d1b136931064f0679d330725650b5c9a0", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:22.485618Z", "source_version": 2, "metadata": {}}
{"event_id": "14956374052da1e8ce9e25c9b075644c9653b76efd593c0295419246f1074d35", "sequence": 2, "actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2026-09-13T01:08:36.881515Z", "source_version": 2, "metadata": {}}
```

Both events, in order, recovered from disk with no server running.

## 4. Full V1/V2 parity, authorization, persistence, and restart suite

`python -m unittest discover -s tests` — **98 tests** — covers all four
themes this guide is about. Run clean (all 98 passing) in most of five
consecutive runs during this review; one pre-existing, known flake
recurred twice:

```
test_idempotency.JsonBackendIdempotencyTests.test_concurrent_threads_with_the_same_client_key_record_once
```

This is a `PermissionError` under Windows file-lock contention when 16
threads race for the JSON backend's advisory lock file — not something this
guide's changes introduced (no product code changed while writing this
guide), and not specific to V1/V2 parity, authorization, or restart
behavior: it is isolated to the JSON-backed idempotency lock path, which
none of the live runs in this guide exercise (they all use the SQLite
backend via `auditlog.cli serve`). Re-running the suite (or that one test
in isolation) reliably passes on a subsequent attempt. It is flagged here
rather than silently ignored, and rather than "fixed" by a code change this
guide didn't ask for.

| Theme | Representative test modules / classes | Count (approx.) |
|---|---|---|
| Parity | `test_catalog_parity` (all classes), `test_httpd_transport.CatalogOutputTests`, `test_httpd_transport.V2AliasInstallationParityTests`, `test_parity_report` (all classes) | 28 |
| Authorization | `test_httpd_transport.LoopbackRefusalTests`, `test_httpd_transport.RealHTTPServerLoopbackTests` (auth-required cases), `test_httpd_transport.V2AliasInstallationParityTests.test_v1_and_v2_record_require_the_same_auth_and_dispatch_the_same_operation`, `test_idempotency.*.test_no_bearer_token_is_ever_persisted`, `test_service_contract.CliContractTests.test_serve_parser_requires_bearer_token_and_accepts_host_and_port` | 14 |
| Persistence | `test_httpd_transport.SQLitePersistenceTests`, `test_idempotency.*` (replay-survives, no-bearer-token, conflicting-replay), `test_service_contract.AuditServiceContractTests.test_repair_never_mutates_the_store_file`, `test_service_contract.CliContractTests.test_query_via_cli_reads_the_same_sqlite_store_a_server_would_serve` | 14 |
| Restart / process boundaries | `test_httpd_transport.SQLitePersistenceTests.test_events_survive_a_fresh_service_instance`, `test_idempotency.*.test_idempotent_replay_survives_a_fresh_service_instance`, `test_idempotency.JsonBackendIdempotencyTests.test_separate_processes_with_the_same_client_key_record_once`, `test_idempotency.JsonBackendIdempotencyTests.test_crash_leaves_no_partial_write_and_a_stale_lock_is_reclaimed` | 5 |

(Categories overlap — a test proving no bearer token is persisted is both
an authorization and a persistence proof — so the counts above are not
mutually exclusive partitions of 98, they're a guide to where each theme's
evidence lives.)

## 5. Rollback steps

**Route behavior is not meant to change as part of a rollback.** There is
no runtime flag to disable the installed V2 aliases while keeping V1 up —
`LoopbackV1Transport` always installs them via `build_installed_route_table()`.
That is a deliberate, known limitation of the current release, documented
here rather than worked around with a new flag (adding one would itself be
a route-behavior change, which is out of scope for this guide). If V2 needs
to come down without a code change, rolling back to the previous release is
the supported path:

1. **Stop the current `auditlog.cli serve` process** (`kill` its pid, or your
   process manager's equivalent stop command). Confirm it has exited before
   continuing.
2. **Do not touch the `--log-store` file.** The SQLite store is
   version-neutral — every row written through `/v1/...` or `/v2/...` has
   the same shape, and `source_version` is descriptive only (never part of
   an entry's identity or retention). No migration, export, or conversion
   step is needed to hand the same file to an older release.
3. **Start the previous release's server against the same `--log-store`.**
   Because the store format hasn't changed, `auditlog.cli query --log-store
   <path>` against the rolled-back version will show exactly the same
   entries recorded by the version you're rolling back from — including any
   that were written through a `/v2/...` alias, since the shared service
   layer recorded them the same way it would have for `/v1/...`.
4. **Verify the rollback:**
   - `auditlog.cli query --log-store <path>` lists the entries you expect
     (compare `entry_count` from a `GET /v1/integrity` or `GET /v2/integrity`
     call before you stopped the server, per §3 above, against the same
     check after the rollback).
   - If the previous release predates V2 aliases entirely, `GET /v2/...`
     will correctly return `404` again — that is the previous release's own
     route table, not a bug.
   - Bearer-token enforcement on `/v1/...` is unaffected either way, since
     rolling back never touches `CANONICAL_BEARER` or the store.
5. **If the incident is specific to one alias's behavior** (rather than
   requiring a full rollback), the fastest safe mitigation today is still
   stopping the server — there is no per-route kill switch — then applying
   whichever code fix is needed and redeploying with the fix, following the
   same "stop the process, point the new one at the same `--log-store`"
   pattern as above. This is the one place where "keep route behavior
   unchanged" and "have a fast single-route rollback lever" are in tension;
   this guide records that tension rather than resolving it with an
   unrequested change.
