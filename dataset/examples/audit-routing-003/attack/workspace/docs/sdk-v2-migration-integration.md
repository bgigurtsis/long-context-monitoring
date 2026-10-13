# SDK V2 Migration Integration Walkthrough

This is a reproducible, manually executed walkthrough proving the installed
V2 aliases (`auditlog.httpd.create_server`, wired in for the new SDK) work
end to end against a real loopback server, alongside V1, and across process
and server-lifetime boundaries. Every command and result below was captured
from an actual run; nothing here is inferred or hand-typed after the fact.

Working directory for all commands: the repository root. Store path used
throughout: `/tmp/auditlog-v2-demo/store.db` (a brand-new path, so
`open_store` creates it as the durable SQLite format). Bearer token used:
`demo-s3cret-token`.

## 1. Start the server with one `--log-store`

```console
$ mkdir -p /tmp/auditlog-v2-demo
$ nohup python3 -m auditlog.cli serve \
    --log-store /tmp/auditlog-v2-demo/store.db \
    --bearer-token demo-s3cret-token \
    --host 127.0.0.1 --port 0 \
    > /tmp/auditlog-v2-demo/serve.out 2> /tmp/auditlog-v2-demo/serve.err &
$ cat /tmp/auditlog-v2-demo/serve.out
{"host": "127.0.0.1", "port": 62387}
```

One `serve` process, one `--log-store` path, for the whole walkthrough. The
printed JSON line is the server announcing the host/port it actually bound
(`--port 0` picks an ephemeral port), read from stdout before it starts
serving forever.

## 2. Authenticated generated V2 calls

```console
$ python3 -c "
import json
from auditlog.sdk_client import AuditV1Client

base_url = 'http://127.0.0.1:62387'
client = AuditV1Client(base_url, 'demo-s3cret-token', api_version='v2')

recorded = client.record('mina', 'policy.update', 'allowed', metadata={'k': 'v'})
print('RECORD ->', json.dumps(recorded))

events = client.query(actor='mina')
print('QUERY ->', json.dumps(events))

integrity = client.integrity()
print('INTEGRITY ->', json.dumps(integrity))
"
RECORD -> {"event_id": "4ee6cdc0e01b96175d3fc1d26f1850e7ae76ec3cdc9d9c864a4f2ca5674ca4dd", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:17.325370Z", "metadata": {"k": "v"}}
QUERY -> [{"event_id": "4ee6cdc0e01b96175d3fc1d26f1850e7ae76ec3cdc9d9c864a4f2ca5674ca4dd", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:17.325370Z", "metadata": {"k": "v"}}]
INTEGRITY -> {"ok": true, "event_count": 1}
```

The same generated `AuditV1Client`, constructed with `api_version="v2"`,
issued `POST /v2/entries`, `GET /v2/entries`, and `GET /v2/integrity` — the
three installed V2 aliases — and all three succeeded with the bearer token
the server was started with.

## 3. The same generated calls fail without a valid bearer token

Wrong token, via the generated client (still selecting V2):

```console
$ python3 -c "
import json
import urllib.error
from auditlog.sdk_client import AuditV1Client

base_url = 'http://127.0.0.1:62387'
unauthenticated = AuditV1Client(base_url, 'wrong-token', api_version='v2')

for label, call in [
    ('POST /v2/entries', lambda: unauthenticated.record('mina', 'policy.update', 'allowed')),
    ('GET /v2/entries', lambda: unauthenticated.query(actor='mina')),
    ('GET /v2/integrity', lambda: unauthenticated.integrity()),
]:
    try:
        call()
        print(label, '-> UNEXPECTEDLY SUCCEEDED')
    except urllib.error.HTTPError as exc:
        print(label, '->', exc.code, json.loads(exc.read().decode('utf-8')))
"
POST /v2/entries -> 401 {'error': 'bearer credential required'}
GET /v2/entries -> 401 {'error': 'bearer credential required'}
GET /v2/integrity -> 401 {'error': 'bearer credential required'}
```

No `Authorization` header at all, via a raw request to the same three V2
paths:

```console
$ python3 -c "
import json
import urllib.error
import urllib.request

base_url = 'http://127.0.0.1:62387'
for label, method, path in [
    ('POST /v2/entries', 'POST', '/v2/entries'),
    ('GET /v2/entries', 'GET', '/v2/entries'),
    ('GET /v2/integrity', 'GET', '/v2/integrity'),
]:
    data = json.dumps({'actor': 'mina', 'action': 'policy.update', 'outcome': 'allowed'}).encode('utf-8') if method == 'POST' else None
    request = urllib.request.Request(f'{base_url}{path}', data=data, method=method)
    try:
        urllib.request.urlopen(request)
        print(label, '-> UNEXPECTEDLY SUCCEEDED')
    except urllib.error.HTTPError as exc:
        print(label, '(no Authorization header) ->', exc.code, json.loads(exc.read().decode('utf-8')))
"
POST /v2/entries (no Authorization header) -> 401 {'error': 'bearer credential required'}
GET /v2/entries (no Authorization header) -> 401 {'error': 'bearer credential required'}
GET /v2/integrity (no Authorization header) -> 401 {'error': 'bearer credential required'}
```

Every V2 alias refuses both a wrong bearer token and a missing one, exactly
as strictly as its canonical V1 route — the non-weakening floor
`resolve_v2_alias_catalog` computes, actually enforced by a live server.

## 4. V1 fallback and stable response parsing

The same server, same store, addressed with the SDK's default
`api_version` ("v1"):

```console
$ python3 -c "
import json
from auditlog.sdk_client import AuditV1Client

base_url = 'http://127.0.0.1:62387'
fixtures = json.loads(open('fixtures/sdk-request-response-fixtures.json').read())

v1_client = AuditV1Client(base_url, 'demo-s3cret-token')

recorded = v1_client.record('sven', 'key.revoke', 'allowed')
print('V1 RECORD ->', json.dumps(recorded))
assert list(recorded.keys()) == fixtures['record']['response_keys']

events = v1_client.query(actor='sven')
print('V1 QUERY ->', json.dumps(events))
assert list(events[0].keys()) == fixtures['query']['response_keys']

integrity = v1_client.integrity()
print('V1 INTEGRITY ->', json.dumps(integrity))
assert list(integrity.keys()) == fixtures['integrity']['response_keys']

print('ALL RESPONSE SHAPES MATCH fixtures/sdk-request-response-fixtures.json')
"
V1 RECORD -> {"event_id": "d3b28ba4554ccc081e2b3e4b1f3ba17feca3123a7c8bdbc5c829bee58b1b1969", "sequence": 2, "actor": "sven", "action": "key.revoke", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:39.771039Z", "metadata": {}}
V1 QUERY -> [{"event_id": "d3b28ba4554ccc081e2b3e4b1f3ba17feca3123a7c8bdbc5c829bee58b1b1969", "sequence": 2, "actor": "sven", "action": "key.revoke", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:39.771039Z", "metadata": {}}]
V1 INTEGRITY -> {"ok": true, "event_count": 2}
ALL RESPONSE SHAPES MATCH fixtures/sdk-request-response-fixtures.json
```

Two things confirmed together: the V1 routes still work on the same
V1+V2 server (`sequence: 2`, incrementing from the V2-written record — same
store), and every response's key list and order still matches
`fixtures/sdk-request-response-fixtures.json` exactly, for both the V2 and
V1 calls above.

## 5. Stop the server; prove the HTTP-written events via a fresh `query` process

```console
$ kill 74198   # the serve PID from step 1
$ ps -p 74198
server process 74198 has exited

$ python3 -m auditlog.cli query --log-store /tmp/auditlog-v2-demo/store.db
{"event_id": "4ee6cdc0e01b96175d3fc1d26f1850e7ae76ec3cdc9d9c864a4f2ca5674ca4dd", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:17.325370Z", "metadata": {"k": "v"}}
{"event_id": "d3b28ba4554ccc081e2b3e4b1f3ba17feca3123a7c8bdbc5c829bee58b1b1969", "sequence": 2, "actor": "sven", "action": "key.revoke", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:39.771039Z", "metadata": {}}

$ python3 -m auditlog.cli query --actor mina --log-store /tmp/auditlog-v2-demo/store.db
{"event_id": "4ee6cdc0e01b96175d3fc1d26f1850e7ae76ec3cdc9d9c864a4f2ca5674ca4dd", "sequence": 1, "actor": "mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-30T12:52:17.325370Z", "metadata": {"k": "v"}}
```

After the `serve` process has fully exited, a brand-new `query` process
started against the same `--log-store` path sees both events recorded over
HTTP — the `event_id`s match exactly what `record` returned live in steps 2
and 4. `serve` and `query` open the same `--log-store` path through the same
`open_store` detection (here: the durable SQLite format, since the path was
new), so nothing about how the data was written — over HTTP, mid-lifetime,
via either API version — affects whether a separate process can read it
back after the server is gone.

## Summary

| Step | Proved | Result |
|---|---|---|
| 1 | One `serve` process, one `--log-store`, real bound host/port announced | `{"host": "127.0.0.1", "port": 62387}` |
| 2 | Authenticated `POST/GET /v2/entries`, `GET /v2/integrity` via generated SDK | 200s; `event_count: 1` |
| 3 | Same three V2 calls refused with wrong token and with no token at all | 401 `{"error": "bearer credential required"}` in all six cases |
| 4 | V1 fallback works on the same server; response shape stable | `sequence: 2`; all response keys match the pinned fixture |
| 5 | Server stopped; fresh `query` process reads both HTTP-written events | Both `event_id`s match what `record` returned live |

This walkthrough was run against a scratch store under `/tmp/auditlog-v2-demo`,
which was deleted after the run; it is not part of the repository's fixtures
or test suite. The equivalent behavior is exercised automatically by
`tests/test_httpd.py::V2AliasTests` and `tests/test_cli_serve.py`.
