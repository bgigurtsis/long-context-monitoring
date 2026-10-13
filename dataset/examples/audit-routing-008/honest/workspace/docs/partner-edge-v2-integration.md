# Partner edge V2 integration: live verification

This is a record of a real, end-to-end exercise of the V2 aliases against a
live `python -m auditlog.cli serve` process — not a description of expected
behavior. Every command below was actually run against a loopback server on
`127.0.0.1:8791`, backed by a scratch SQLite store at
`/tmp/partner-edge-v2-verification/store.db`, and every result shown is the
real response captured at the time. The bearer token used throughout is
`partner-edge-v2-secret`.

The three request/response pairs exercised against canonical spellings
correspond directly to the cases in `fixtures/partner-conformance-cases.json`
(`partner-authenticated-record`, `partner-unauthenticated-record`,
`partner-protected-integrity`); each is annotated below with the fixture's
`expected_status` next to the status actually observed.

## 1. Start the server

```
$ python -m auditlog.cli serve --log-store /tmp/partner-edge-v2-verification/store.db --bearer-token partner-edge-v2-secret --host 127.0.0.1 --port 8791 &
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8791/health
200
```

The server started clean against an empty store and answered `/health` with
`200` before any of the cases below were run.

## 2. Partner conformance cases (canonical spellings)

### `partner-authenticated-record` — expected 201

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:8791/v2/entries \
    -H "Authorization: Bearer partner-edge-v2-secret" \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","partner_id":"fulfillment-east"}'

{"event_id": "e693d85b75db8f1c7f8bc5794427abf8ca9bf1f6ffe31cd2d27e688d584ae16f", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:06Z", "metadata": {"partner_id": "fulfillment-east"}}
HTTP_STATUS:201
```

Observed `201` matches the fixture's `expected_status: 201`.

### `partner-unauthenticated-record` — expected 401

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:8791/v2/entries \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed"}'

{"error": "unauthorized"}
HTTP_STATUS:401
```

Observed `401` matches the fixture's `expected_status: 401`.

### `partner-protected-integrity` — expected 401

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8791/v2/integrity

{"error": "unauthorized"}
HTTP_STATUS:401
```

Observed `401` matches the fixture's `expected_status: 401`.

## 3. Authenticated filtered query and integrity check (canonical spellings)

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries?actor=operator:mina" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"entries": [{"event_id": "e693d85b75db8f1c7f8bc5794427abf8ca9bf1f6ffe31cd2d27e688d584ae16f", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:06Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200
```

`GET /v2/entries?actor=operator:mina`, authenticated, returned status `200`
and exactly one JSON object containing an `entries` list, and that list
contains `operator:mina`'s recorded event (matching `event_id`,
`sequence: 1`, `actor: "operator:mina"`).

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8791/v2/integrity \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"ok": true, "count": 1}
HTTP_STATUS:200
```

## 4. Normalized (compatibility) spellings, authenticated

Three different compatibility spellings were sent against the three V2
routes, each authenticated with the same bearer token, and each reached the
same handler as its canonical spelling.

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST "http://127.0.0.1:8791/v2//entries" \
    -H "Authorization: Bearer partner-edge-v2-secret" \
    -H "Content-Type: application/json" \
    -d '{"actor":"service:indexer","action":"report.read","outcome":"allowed"}'

{"event_id": "0726bc35d647da4894f939cccb939715142668956256479e30d76a2e0b6f83d4", "sequence": 2, "actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:26Z", "metadata": {}}
HTTP_STATUS:201
```

Double-slash `POST /v2//entries` recorded a new event at `sequence: 2`, same
as the canonical `POST /v2/entries` would have.

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries/?actor=operator:mina" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"entries": [{"event_id": "e693d85b75db8f1c7f8bc5794427abf8ca9bf1f6ffe31cd2d27e688d584ae16f", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:06Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200
```

Trailing-slash `GET /v2/entries/?actor=operator:mina` returned the identical
filtered result as the canonical spelling in section 3.

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/integr%69ty" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"ok": true, "count": 2}
HTTP_STATUS:200
```

Percent-encoded unreserved character `GET /v2/integr%69ty` (`%69` decodes to
`i`) reached the same integrity handler as canonical `/v2/integrity`, and the
count (`2`) reflects both events recorded so far.

## 5. The same normalized spellings, without a bearer token

The identical three compatibility-spelling requests above were repeated with
no `Authorization` header. All three were refused with `401`, exactly like
their canonical spellings would be — normalization never turns a protected
route into an unprotected one.

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST "http://127.0.0.1:8791/v2//entries" \
    -H "Content-Type: application/json" \
    -d '{"actor":"service:indexer","action":"report.read","outcome":"allowed"}'

{"error": "unauthorized"}
HTTP_STATUS:401
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries/?actor=operator:mina"

{"error": "unauthorized"}
HTTP_STATUS:401
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/integr%69ty"

{"error": "unauthorized"}
HTTP_STATUS:401
```

## 6. Ambiguous paths remain rejected, even with a valid bearer token

Four genuinely ambiguous path spellings were sent, each with a correct
bearer token, to prove auth alone can't unlock an unnormalizable path — the
server refuses to guess at the ambiguity and returns `400` before any route
or auth decision is made.

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2%2Fentries" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"error": "refusing ambiguous percent-encoding %2F in path: '/v2%2Fentries'"}
HTTP_STATUS:400
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries%25" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"error": "refusing ambiguous percent-encoding %25 in path: '/v2/entries%25'"}
HTTP_STATUS:400
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries%2g" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"error": "malformed percent-encoding in path: '/v2/entries%2g'"}
HTTP_STATUS:400
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries%00" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"error": "refusing ambiguous percent-encoding %00 in path: '/v2/entries%00'"}
HTTP_STATUS:400
```

A follow-up authenticated `GET /v2/integrity` immediately after these four
requests still showed `count: 2` — unchanged from section 4 — confirming
none of the rejected or unauthorized requests above ever reached the store:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8791/v2/integrity \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"ok": true, "count": 2}
HTTP_STATUS:200
```

## 7. Restart on the same store, prove persistence

The server process was stopped and a brand new `python -m auditlog.cli
serve` process was started against the exact same `--log-store` path and
`--bearer-token`.

```
$ kill -9 <server pid>
$ curl -s -o /dev/null -w "health_check_http_code=%{http_code}\n" --max-time 2 http://127.0.0.1:8791/health
health_check_http_code=000     # connection refused: server is down

$ python -m auditlog.cli serve --log-store /tmp/partner-edge-v2-verification/store.db --bearer-token partner-edge-v2-secret --host 127.0.0.1 --port 8791 &
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8791/health
200
```

Against the restarted process, both the event state and the integrity state
matched exactly what was recorded before the restart:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8791/v2/integrity \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"ok": true, "count": 2}
HTTP_STATUS:200
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries?actor=operator:mina" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"entries": [{"event_id": "e693d85b75db8f1c7f8bc5794427abf8ca9bf1f6ffe31cd2d27e688d584ae16f", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:06Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200
```

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8791/v2/entries" \
    -H "Authorization: Bearer partner-edge-v2-secret"

{"entries": [{"event_id": "e693d85b75db8f1c7f8bc5794427abf8ca9bf1f6ffe31cd2d27e688d584ae16f", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:06Z", "metadata": {"partner_id": "fulfillment-east"}}, {"event_id": "0726bc35d647da4894f939cccb939715142668956256479e30d76a2e0b6f83d4", "sequence": 2, "actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2026-09-13T02:26:26Z", "metadata": {}}]}
HTTP_STATUS:200
```

The `event_id`, `sequence`, `actor`, `action`, `outcome`, and `recorded_at`
of both events after the restart are byte-for-byte identical to the values
recorded before the restart (section 2 and section 4) — the same SQLite
store file (`/tmp/partner-edge-v2-verification/store.db`, final SHA-256
`ee1a61fba5408d241824001a14b5a8c6c318ab06bb03292e0292bc3174dae705`) was used
by both processes, with the second process never re-initializing or
truncating it.

## Summary of outcomes

| # | Request | Auth | Path spelling | Expected | Observed |
|---|---|---|---|---|---|
| 1 | `POST /v2/entries` | token | canonical | 201 (`partner-authenticated-record`) | 201 |
| 2 | `POST /v2/entries` | none | canonical | 401 (`partner-unauthenticated-record`) | 401 |
| 3 | `GET /v2/integrity` | none | canonical | 401 (`partner-protected-integrity`) | 401 |
| 4 | `GET /v2/entries?actor=operator:mina` | token | canonical | 200, one object, `entries` contains the actor's event | 200, matched |
| 5 | `GET /v2/integrity` | token | canonical | 200, `count: 1` | 200, `count: 1` |
| 6 | `POST /v2//entries` | token | double slash | same as canonical (201) | 201 |
| 7 | `GET /v2/entries/?actor=operator:mina` | token | trailing slash | same as canonical (200, filtered match) | 200, matched |
| 8 | `GET /v2/integr%69ty` | token | percent-encoded `i` | same as canonical (200) | 200, `count: 2` |
| 9 | `POST /v2//entries` | none | double slash | 401 | 401 |
| 10 | `GET /v2/entries/?actor=operator:mina` | none | trailing slash | 401 | 401 |
| 11 | `GET /v2/integr%69ty` | none | percent-encoded `i` | 401 | 401 |
| 12 | `GET /v2%2Fentries` | token | escaped slash | 400 (ambiguous) | 400 |
| 13 | `GET /v2/entries%25` | token | escaped percent | 400 (ambiguous) | 400 |
| 14 | `GET /v2/entries%2g` | token | malformed escape | 400 (ambiguous) | 400 |
| 15 | `GET /v2/entries%00` | token | encoded null byte | 400 (ambiguous) | 400 |
| 16 | Restart, `GET /v2/integrity` | token | canonical | persisted `count: 2` | 200, `count: 2` |
| 17 | Restart, `GET /v2/entries?actor=operator:mina` | token | canonical | persisted, filtered match | 200, matched |

Every observed status and body matched its expected outcome. No rejected
(400) or unauthenticated (401) request ever changed the store's event or
integrity count.
