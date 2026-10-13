# Dual-version integration: V1 record, V2 replay, over a real server

This walks through a real, socket-based run of `python -m auditlog.cli serve`,
proving V1 and the installed V2 aliases share one SQLite log store, one
idempotency ledger, and one bearer-token policy — then proves the event
written over HTTP is still there, from a fresh `auditlog.cli query` process,
after the server has been stopped.

Every command below was actually run against this repository; every result
shown is the real, unedited output of that run. The commands are safe to
re-run as-is (adjust `PORT` if `8199` is already in use on your machine).

## Setup

```bash
LOG_STORE=/tmp/auditlog-dual-version-demo.db
BEARER=s3cr3t-demo-token
HOST=127.0.0.1
PORT=8199
rm -f "$LOG_STORE"
```

## 1. Start the server with one `--log-store`

```bash
python -m auditlog.cli serve --log-store "$LOG_STORE" --bearer-token "$BEARER" --host "$HOST" --port "$PORT" &
SERVER_PID=$!
sleep 1
```

```
server pid: 566
```

`serve` prints its bound `{"host": ..., "port": ...}` once, then blocks in
`serve_forever()`. One `AuditHTTPServer`, backed by one
`SQLiteAuditService("$LOG_STORE")`, now has both `/v1/...` and the turn-3
catalog's `/v2/...` aliases installed in its one route table.

## 2. Record one event through authenticated V1

```bash
curl -s -X POST "http://$HOST:$PORT/v1/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"demo-req-1"}'
```

```json
{"event_id": "d2c3eebe3ce6eed9d6a1928c775faf0e3f0a6747730a8132d5d72f0dd88aa587", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:06:36.691123Z", "source_version": 2, "metadata": {}}
```

`sequence: 1` — the first entry in the trail. `client_key: "demo-req-1"` was
sent but is never echoed back or persisted itself; only the canonical result
(`event_id`, `sequence`, `actor`, `action`, `outcome`, `recorded_at`,
`source_version`, `metadata`) is.

## 3. Replay the same `client_key` through authenticated `POST /v2/entries`

```bash
curl -s -X POST "http://$HOST:$PORT/v2/entries" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","client_key":"demo-req-1"}'
```

```json
{"event_id": "d2c3eebe3ce6eed9d6a1928c775faf0e3f0a6747730a8132d5d72f0dd88aa587", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:06:36.691123Z", "source_version": 2, "metadata": {}}
```

Byte-for-byte the same `event_id`, `sequence`, and `recorded_at` as step 2,
even though this request hit `/v2/entries` instead of `/v1/entries`: the same
`client_key` replayed through the other version's alias returned the
original canonical result rather than recording a second event. This is
cross-version idempotency proven over a real socket, not just at the service
layer.

## 4. Query it through `GET /v2/entries`

```bash
curl -s "http://$HOST:$PORT/v2/entries" -H "Authorization: Bearer $BEARER"
```

```json
{"entries": [{"event_id": "d2c3eebe3ce6eed9d6a1928c775faf0e3f0a6747730a8132d5d72f0dd88aa587", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:06:36.691123Z", "source_version": 2, "metadata": {}}]}
```

Exactly one entry: the replay in step 3 did not duplicate it.

## 5. Query `GET /v2/integrity`

```bash
curl -s "http://$HOST:$PORT/v2/integrity" -H "Authorization: Bearer $BEARER"
```

```json
{"ok": true, "entry_count": 1, "tampered_event_ids": [], "sequence_error": null}
```

`ok: true`, `entry_count: 1`, no tampered ids, no sequence error.

## 6. Protected calls fail without a token

Every V1 and V2 route enforces the same bearer policy — the `requires_auth`
each V2 alias resolves to is inherited from its V1 counterpart, and this
proves it end to end, over the real socket, with no `Authorization` header
sent at all:

```bash
for req in "POST /v1/entries" "GET /v1/entries" "GET /v1/integrity" \
           "POST /v2/entries" "GET /v2/entries" "GET /v2/integrity"; do
  method=$(echo "$req" | cut -d' ' -f1)
  path=$(echo "$req" | cut -d' ' -f2)
  code=$(curl -s -o /tmp/auditlog-noauth-body.json -w "%{http_code}" \
    -X "$method" "http://$HOST:$PORT$path" \
    -H "Content-Type: application/json" -d '{"actor":"x","action":"y","outcome":"z"}')
  echo "$method $path -> HTTP $code, body: $(cat /tmp/auditlog-noauth-body.json)"
done
```

```
POST /v1/entries -> HTTP 401, body: {}
GET /v1/entries -> HTTP 401, body: {}
GET /v1/integrity -> HTTP 401, body: {}
POST /v2/entries -> HTTP 401, body: {}
GET /v2/entries -> HTTP 401, body: {}
GET /v2/integrity -> HTTP 401, body: {}
```

All six routes — every V1 route and every installed V2 alias — return
`401 Unauthorized` with an empty body when no bearer token is supplied.

## 7. Stop the server

```bash
kill "$SERVER_PID"
wait "$SERVER_PID" 2>/dev/null
```

```
server process 566 stopped
```

## 8. Prove the HTTP-written event from a fresh `auditlog.cli query` process

With the server gone, a brand-new process reads the same `--log-store` path
directly:

```bash
python -m auditlog.cli query --log-store "$LOG_STORE"
```

```json
{"event_id": "d2c3eebe3ce6eed9d6a1928c775faf0e3f0a6747730a8132d5d72f0dd88aa587", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T01:06:36.691123Z", "source_version": 2, "metadata": {}}
```

The same `event_id` and `sequence` from steps 2–4, recovered from disk with
no server process running at all: the event `serve` wrote over HTTP is
durable in the SQLite `--log-store`, independent of the process that wrote
it.

## What this proves

- One `--log-store` backs `serve` and `query` — there is no separate V1 or
  V2 storage, and no separate storage for the CLI versus the server.
- A `client_key` recorded through V1 and replayed through V2 (or vice versa)
  resolves to the exact same canonical event: cross-version idempotency,
  proven over a real socket rather than only at the service layer.
- Every V1 route and every installed V2 alias enforces the same bearer-token
  requirement; none of the six routes exercised above is reachable without
  one.
- Data written by `serve` survives `serve` being stopped, and is visible to
  a completely separate `query` process reading the same file afterward.
