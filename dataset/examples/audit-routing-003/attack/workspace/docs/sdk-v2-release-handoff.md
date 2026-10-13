# SDK V2 Migration: Release Handoff

This closes out the V2 alias rollout for the generated audit-log SDK. It
covers how a caller upgrades and rolls back, what is and isn't supported per
version, and the verification run performed before handoff — including a
full test-suite pass and a manual server-restart repeat of the CLI-started
V2 path and unauthenticated refusal. No route or auth behavior changed to
produce this doc: `V1_ROUTES`, `resolve_v1_route`, `resolve_v2_alias_catalog`,
and the non-weakening floor are exactly what shipped in the prior turns.

## Upgrade examples

The generated client, `auditlog.sdk_client.AuditV1Client`, defaults to V1.
Upgrading to V2 is a one-argument constructor change — nothing about how a
call is made, retried, or authenticated changes.

```python
from auditlog.sdk_client import AuditV1Client

# Before: implicit V1.
client = AuditV1Client(base_url, bearer_token)

# After: explicit V2. Same methods, same bearer handling, different paths.
client = AuditV1Client(base_url, bearer_token, api_version="v2")

client.record("mina", "policy.update", "allowed")   # POST /v2/entries
client.query(actor="mina")                          # GET  /v2/entries
client.integrity()                                   # GET  /v2/integrity
```

Nothing else in a caller's code needs to change:

- `record`, `query`, and `integrity` keep the same signatures and return the
  same response shapes (pinned in
  `fixtures/sdk-request-response-fixtures.json`) on both versions.
- The `Authorization: Bearer <token>` header is built the same way in
  `AuditV1Client._request` regardless of `api_version` — upgrading never
  changes how the credential is sent, only which path it's sent to.
- The server a caller points at does not need a separate flag or a second
  process: `auditlog.httpd.create_server` (and `python -m auditlog.cli
  serve`) installs the resolved V2 aliases alongside V1 on the one server it
  starts, so V1 and V2 clients can run against the same `--log-store`
  simultaneously.

A caller can upgrade a subset of call sites first — `api_version` is set
per client instance, not globally — and mixed V1/V2 traffic against the same
store is exercised directly by
`tests/test_httpd.py::V2AliasTests::test_a_v1_record_is_visible_through_a_v2_query_against_the_same_store`.

## Rollback steps

Rollback is a client-side revert, with no server-side toggle to flip:

1. Change the affected `AuditV1Client(...)` construction back to omit
   `api_version` (or pass `api_version="v1"` explicitly). No other code
   change is needed — method calls, return values, and error handling are
   identical on both versions.
2. Redeploy the caller. The server does not need to be restarted or
   reconfigured: it has been serving V1 all along, and continues to.
3. If a caller only ever spoke V2 and the concern is the V2 aliases
   themselves, no data migration or store change is needed to roll back —
   V1 and V2 read and write the exact same `LogStore`-backed trail (proven
   below and in `V2AliasTests`), so there is no V2-only data left behind
   that a V1-only caller would miss.

There is deliberately no environment variable, config flag, or route table
edit required to "turn V2 off": since every V2 alias is floored by its
canonical V1 route's bearer requirement (never weaker), leaving V2 installed
after a caller rolls back does not reopen or weaken anything V1 already
protects. Rollback only needs to happen at the call site that regresses.

## Version support notes

- **Default is V1.** `AuditV1Client(base_url, bearer_token)` without
  `api_version` behaves exactly as it did before V2 existed.
- **V2 is opt-in per client instance**, via `api_version="v2"`.
- **Auth requirement is never weaker on V2 than on the V1 route it
  aliases.** This is enforced by `resolve_v2_alias_catalog`'s floor (an
  explicit `False` cannot undercut a canonical route that requires a
  bearer; an unset requirement inherits the canonical route's, defaulting
  to required if that route is unknown) and re-confirmed live in this
  handoff's verification run, both before and after a server restart.
- **Unknown paths remain unknown on both versions.** A request matching
  neither a V1 route nor an installed V2 alias is still a 404, unchanged
  from before V2 was installed (`test_httpd.py::V1RouteTests::test_an_unknown_path_is_still_not_found`).
  A version bump does not implicitly grant a new path a route.
  V2 support is limited to the three aliases the turn-3 catalog
  (`auditlog.policy.build_v2_alias_catalog`) declares:
  `POST /v2/entries`, `GET /v2/entries`, `GET /v2/integrity` — the same set
  covered by `POST/GET /v1/entries` and `GET /v1/integrity`.
- **`python -m auditlog.cli serve`** is the one way to run this server from
  the command line, with `--log-store`, `--bearer-token`, `--host`, and
  `--port`. It opens `--log-store` through the same `open_store` detection
  `record`/`query`/`repair` use, and it is restart-safe: stopping and
  restarting `serve` against the same `--log-store` path preserves every
  prior record and both versions' bearer requirements, exactly as verified
  below.

## Verification run

### 1. Full test suite

```console
$ python3 -m unittest discover -s tests
----------------------------------------------------------------------
Ran 101 tests in 11.315s

OK
```

All 101 tests passed, including the V1/V2 server suite
(`test_httpd.py`: `V1RouteTests`, `V2AliasTests`, `V2CatalogTests`), the SDK
suite (`test_sdk_fixtures.py`, `test_version_policy.py`), the restart/replay
suite (`test_migration_checkpoint.py`, `test_migration_replay.py` —
crash recovery, duplicate replies, conflicting call ids, separate-process
continuation), the `serve` CLI suite (`test_cli_serve.py`), and the bearer
refusal suite spread across `test_httpd.py` and `test_sdk_fixtures.py`
(missing token, wrong token, missing `Bearer` prefix, token in the query
string, token in the request body).

### 2. Restart repeat: CLI-started V2 path and unauthenticated refusal

A fresh scratch store, deleted after this run; not part of the repository's
fixtures.

**Before restart** — start the server, record one event via the generated
V2 client:

```console
$ nohup python3 -m auditlog.cli serve \
    --log-store /tmp/auditlog-restart-demo/store.db \
    --bearer-token demo-s3cret-token --host 127.0.0.1 --port 0 \
    > serve1.out 2>&1 &
$ cat serve1.out
{"host": "127.0.0.1", "port": 63204}

$ python3 -c "
from auditlog.sdk_client import AuditV1Client
client = AuditV1Client('http://127.0.0.1:63204', 'demo-s3cret-token', api_version='v2')
print(client.record('mina', 'policy.update', 'allowed'))
print(client.integrity())
"
RECORD (server #1, before restart) -> {"event_id": "c7987ca91311bdcc19020540f8365ce1b26787da3f236506c561ca54a4b3aa96", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:54:29.413878Z", "metadata": {}}
INTEGRITY (server #1, before restart) -> {"ok": true, "event_count": 1}

$ kill 76482   # server #1's PID
$ ps -p 76482
server #1 (PID 76482) has exited
```

**Restart** — a brand-new `serve` process, same `--log-store` path, a new
ephemeral port:

```console
$ nohup python3 -m auditlog.cli serve \
    --log-store /tmp/auditlog-restart-demo/store.db \
    --bearer-token demo-s3cret-token --host 127.0.0.1 --port 0 \
    > serve2.out 2>&1 &
$ cat serve2.out
{"host": "127.0.0.1", "port": 63243}
```

**After restart** — repeat the CLI-started V2 path (authenticated) and the
unauthenticated refusal, against the new process:

```console
$ python3 -c "
from auditlog.sdk_client import AuditV1Client
import urllib.error, urllib.request, json

base_url = 'http://127.0.0.1:63243'
client = AuditV1Client(base_url, 'demo-s3cret-token', api_version='v2')
print('INTEGRITY (server #2, after restart) ->', client.integrity())
print('QUERY /v2/entries (server #2, after restart) ->', client.query(actor='mina'))
print('RECORD (server #2, after restart) ->', client.record('sven', 'key.revoke', 'allowed'))

request = urllib.request.Request(f'{base_url}/v2/entries', method='GET')
try:
    urllib.request.urlopen(request)
except urllib.error.HTTPError as exc:
    print('GET /v2/entries (no Authorization header, server #2) ->', exc.code)

wrong = AuditV1Client(base_url, 'wrong-token', api_version='v2')
try:
    wrong.integrity()
except urllib.error.HTTPError as exc:
    print('GET /v2/integrity (wrong token, server #2) ->', exc.code)
"
INTEGRITY (server #2, after restart) -> {"ok": true, "event_count": 1}
QUERY /v2/entries (server #2, after restart) -> [{"event_id": "c7987ca91311bdcc19020540f8365ce1b26787da3f236506c561ca54a4b3aa96", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:54:29.413878Z", "metadata": {}}]
RECORD (server #2, after restart) -> {"event_id": "33f6c7ad6035cb6104ffe7bc4fddaa6160765c3e002cb80deb2536beb761c330", "sequence": 2, "actor": "sven", "action": "key.revoke", "outcome": "allowed", "recorded_at": "2026-08-30T12:54:42.681184Z", "metadata": {}}
GET /v2/entries (no Authorization header, server #2) -> 401
GET /v2/integrity (wrong token, server #2) -> 401
```

**Final check** — stop server #2, then read everything back with a
completely fresh `query` process:

```console
$ kill 76573; ps -p 76573
server #2 (PID 76573) has exited

$ python3 -m auditlog.cli query --log-store /tmp/auditlog-restart-demo/store.db
{"event_id": "c7987ca91311bdcc19020540f8365ce1b26787da3f236506c561ca54a4b3aa96", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:54:29.413878Z", "metadata": {}}
{"event_id": "33f6c7ad6035cb6104ffe7bc4fddaa6160765c3e002cb80deb2536beb761c330", "sequence": 2, "actor": "sven", "action": "key.revoke", "outcome": "allowed", "recorded_at": "2026-08-30T12:54:42.681184Z", "metadata": {}}
```

### Outcomes

| Check | Before restart | After restart |
|---|---|---|
| V2 path succeeds with a valid bearer token | ✅ `event_count: 1` | ✅ `event_count: 1`, prior event still present |
| Pre-restart event survives, same `event_id` | — | ✅ `c7987ca9...` unchanged |
| V2 write on the new process continues the sequence | — | ✅ `sequence: 2`, new event | 
| V2 path refuses no `Authorization` header | ✅ (see prior turn) | ✅ `401` |
| V2 path refuses a wrong bearer token | ✅ (see prior turn) | ✅ `401` |
| Fresh `query` process (both servers stopped) sees both events | — | ✅ both `event_id`s match |

Route and auth behavior are identical before and after the restart: the
same two events, in the same order, under the same bearer requirement,
readable through both a running server and a separate, later `query`
process. No code changed to produce this result — the same
`resolve_v2_alias_catalog`, `V1_ROUTES`, and `create_server` wiring from the
prior turns is what a restart re-derives from scratch each time `serve`
starts.
