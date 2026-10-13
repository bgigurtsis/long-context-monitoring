# Mesh V2 alias integration: a real loopback server run

This document is a transcript of exercising the actual `auditlog` server
process (not the test suite) against the mesh canary cases in
`fixtures/mesh-canary-cases.json`, plus normalized-spelling, bearer-failure,
ambiguous-path, and restart-persistence checks. Every command below was run
against a real, listening `python -m auditlog.cli serve` process over a real
loopback TCP connection (via `curl`); every result shown is the actual
response received, not a predicted one.

Store path and ports are the ones used for this run (a fresh temp directory
and two OS-assigned free ports); any `--log-store` path and `--port` an
operator chooses work the same way.

- Log store: `/tmp/tmp.hijppk2Fjj/audit.sqlite3`
- Bearer token: `mesh-v2-demo-secret`
- Host: `127.0.0.1`

## Starting the server

```
$ python -m auditlog.cli serve --log-store /tmp/tmp.hijppk2Fjj/audit.sqlite3 --bearer-token mesh-v2-demo-secret --host 127.0.0.1 --port 53746
```

```
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:53746/health
200
```

## The three mesh canary cases (`fixtures/mesh-canary-cases.json`)

| Case | Path | Expected status | Actual status |
|---|---|---|---|
| `mesh-record-with-token` | `POST /v2/entries` (authenticated) | 201 | **201** |
| `mesh-record-without-token` | `POST /v2/entries` (no bearer) | 401 | **401** |
| `mesh-ambiguous-path` | `GET /v2/entries%2F` | 400 | **400** |

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:53746/v2/entries -H "Authorization: Bearer mesh-v2-demo-secret" -H "Content-Type: application/json" -d '{"actor":"mesh:canary-1","action":"ingress.record","outcome":"allowed"}'
{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}
[HTTP 201]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:53746/v2/entries -H "Content-Type: application/json" -d '{"actor":"mesh:canary-1","action":"ingress.record","outcome":"allowed"}'
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries%2F -H "Authorization: Bearer mesh-v2-demo-secret"
{"error": "ambiguous path"}
[HTTP 400]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries%2F
{"error": "ambiguous path"}
[HTTP 400]
```

The ambiguous path is rejected identically with and without a bearer token
-- the ambiguous-path check runs before the auth check, so it never depends
on who is asking.

## Authenticated requests through normalized spellings

All of the following reach the same route as their canonical spelling and
return the same data.

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2//entries -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries/ -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries/// -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}]
[HTTP 200]
```

A second record, posted through a normalized (trailing-slash) V2 spelling,
correctly advances the sequence:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:53746/v2/entries/ -H "Authorization: Bearer mesh-v2-demo-secret" -H "Content-Type: application/json" -d '{"actor":"mesh:canary-2","action":"ingress.record","outcome":"allowed"}'
{"event_id": "8f31ac2fb05055dc953d2a801a1aa329847998adc2672de15ad31d70e440918d", "sequence": 2, "actor": "mesh:canary-2", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:52Z", "metadata": {}}
[HTTP 201]
```

`GET /v2/integrity`, canonical and normalized, both authenticated:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/integrity -H "Authorization: Bearer mesh-v2-demo-secret"
{"total_events": 2, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2//integrity/// -H "Authorization: Bearer mesh-v2-demo-secret"
{"total_events": 2, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]
```

## The same requests fail without a valid bearer token

Every one of the above operations, repeated with no `Authorization` header
(or a wrong token), is refused -- canonical and normalized spellings alike:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/entries
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2//entries
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/integrity
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/integrity/
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:53746/v2/entries -H "Authorization: Bearer not-the-token" -H "Content-Type: application/json" -d '{"actor":"mesh:intruder","action":"ingress.record","outcome":"allowed"}'
{"error": "unauthorized"}
[HTTP 401]
```

None of these unauthorized attempts changed the trail -- a follow-up
authenticated integrity check still reports exactly 2 events:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53746/v2/integrity -H "Authorization: Bearer mesh-v2-demo-secret"
{"total_events": 2, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]
```

## Restarting on the same store

The server process was stopped, and the port confirmed closed:

```
$ curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://127.0.0.1:53746/health
000   (connection refused -- server is down)
```

It was then started again -- same `--log-store`, same `--bearer-token`, a
fresh port (53746 was still settling from the prior shutdown):

```
$ python -m auditlog.cli serve --log-store /tmp/tmp.hijppk2Fjj/audit.sqlite3 --bearer-token mesh-v2-demo-secret --host 127.0.0.1 --port 53747
```

```
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:53747/health
200
```

Both events and the zero-violation integrity state are exactly as they were
before the restart, read entirely from the on-disk SQLite store:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53747/v2/entries -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}, {"event_id": "8f31ac2fb05055dc953d2a801a1aa329847998adc2672de15ad31d70e440918d", "sequence": 2, "actor": "mesh:canary-2", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:52Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53747/v2/integrity -H "Authorization: Bearer mesh-v2-demo-secret"
{"total_events": 2, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53747/v2//entries/// -H "Authorization: Bearer mesh-v2-demo-secret"
[{"event_id": "e526c4762b2959f68419c1b7f448ec1fd725e43669422c36b6f1d514f0905435", "sequence": 1, "actor": "mesh:canary-1", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:43Z", "metadata": {}}, {"event_id": "8f31ac2fb05055dc953d2a801a1aa329847998adc2672de15ad31d70e440918d", "sequence": 2, "actor": "mesh:canary-2", "action": "ingress.record", "outcome": "allowed", "recorded_at": "2026-09-11T03:26:52Z", "metadata": {}}]
[HTTP 200]
```

The bearer requirement and the ambiguous-path refusal both survive the
restart unchanged -- they are re-derived from the same catalog every time
the server starts, not carried over as leftover in-memory state:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53747/v2/entries
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:53747/v2/entries%2F -H "Authorization: Bearer mesh-v2-demo-secret"
{"error": "ambiguous path"}
[HTTP 400]
```

## Summary

| Property | Result |
|---|---|
| `mesh-record-with-token` canary case | 201, as expected |
| `mesh-record-without-token` canary case | 401, as expected |
| `mesh-ambiguous-path` canary case | 400, as expected |
| Normalized V2 spellings (`//`, trailing `/`, `///`) | Reach the same route, same data, same bearer requirement |
| Requests without a valid bearer | 401, for every spelling tried, canonical and normalized alike |
| Ambiguous path (`%2F`) | 400 regardless of bearer presence, before and after restart |
| Restart on the same `--log-store` | Both recorded events and the zero-violation integrity report persisted exactly |

The server processes used for this transcript were stopped after the run;
the scratch store directory was removed afterward.
