# Gateway V2 Integration: Live Loopback Verification

This document records a real run of the audit log server through its
documented CLI entry point, followed by real HTTP requests against it over
`127.0.0.1`, proving the installed V2 aliases (`auditlog/httpd.py`,
`auditlog/policy.py`) behave as designed against a live process rather than
only under `unittest`. No test code or application code was modified to
produce this record; it is an exercise of the shipped server as-is.

## 1. Server startup

Command actually run (background process; log store and bearer token are
this run's own throwaway values, port is caller-selected):

```
python -m auditlog.cli serve \
  --log-store gateway-v2-store.sqlite3 \
  --bearer-token gw-v2-integration-secret \
  --host 127.0.0.1 \
  --port 8790
```

Readiness probe (real HTTP `GET /v1/entries` with the correct bearer),
confirming the process was up and serving before any exercise began:

```
python -c "import urllib.request; r = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8790/v1/entries', headers={'Authorization':'Bearer gw-v2-integration-secret'})); print(r.status, r.read())"
```

Result:

```
200 b'{"entries": []}'
```

The server was later stopped cleanly (`TaskStop` on the background process)
once every exercise below had run.

## 2. How every request below was sent

Each request in Sections A–D was sent with Python's `urllib.request` against
the running process at `http://127.0.0.1:8790`, driven by a small script
(`exercise_v2.py`) making one real HTTP call per line — no mocking, no
in-process test client. Each line documents the exact method, path, whether
a bearer token was attached (and which one), and the real response the
server sent back.

## 3. Section A — the supplied gateway compatibility cases

Source: `fixtures/gateway-compatibility-cases.json`, exercised verbatim
against the live server (`canonical-record` implies `POST` given its
`201 Created` expectation; `missing-token` is the same request with the
`Authorization` header withheld):

| case | request | expected_status | actual status | actual body |
|---|---|---|---|---|
| `canonical-record` | `POST /v2/entries` with valid bearer | 201 | **201** | `{"event_id": "098f3083...", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-08-31T19:15:59Z", "metadata": {}}` |
| `missing-token` | `POST /v2/entries` with no bearer | 401 | **401** | `{"error": "bearer token required"}` |

Both fixture cases matched their `expected_status` exactly.

## 4. Section B — authenticated V2 requests through normalized spellings

Every request below carried a valid `Authorization: Bearer
gw-v2-integration-secret` header. Each spelling variant (repeated slash,
trailing slash, printable-ASCII percent-encoding) normalizes to the same
canonical path as the documented spelling per `auditlog/paths.py`, and each
reached the same route with the same result:

| request sent | status | body |
|---|---|---|
| `POST /v2/entries` (canonical) | **201** | `{"event_id": "b5bd6f99...", "sequence": 2, "actor": "svc:gateway", ...}` |
| `POST /v2//entries` (repeated slash) | **201** | `{"event_id": "b5bd6f99...", "sequence": 3, "actor": "svc:gateway", ...}` |
| `POST /v2/%65ntries` (percent-encoded `e`) | **201** | `{"event_id": "b5bd6f99...", "sequence": 4, "actor": "svc:gateway", ...}` |
| `GET /v2/entries` (canonical) | **200** | 4 entries returned |
| `GET /v2/entries/` (trailing slash) | **200** | same 4 entries returned |
| `GET /v2//entries` (repeated slash) | **200** | same 4 entries returned |
| `GET /v2/%65ntries` (percent-encoded `e`) | **200** | same 4 entries returned |
| `GET /v2/integrity` (canonical) | **200** | `{"verified": 4, "tampered": [], "migrated": false, "index_rebuilt": true}` |
| `GET /v2/integrity/` (trailing slash) | **200** | identical report |
| `GET /v2//integrity` (repeated slash) | **200** | identical report |
| `GET /v2/%69ntegrity` (percent-encoded `i`) | **200** | identical report |

Every normalized spelling of `POST /v2/entries`, `GET /v2/entries`, and
`GET /v2/integrity` reached the exact same route as its canonical spelling,
with a valid bearer accepted every time.

Note: the three `POST /v2/entries` calls in this section all carry
identical `(actor, action, outcome, recorded_at)` content (they ran within
the same wall-clock second), so they share one content-derived `event_id`
(`b5bd6f99...`) while still occupying three distinct, gapless sequence
numbers (2, 3, 4) — expected behavior of `AuditService.record`, which
always appends; content-based deduplication is a separate, opt-in concern
(`auditlog/replay.py`), not something the plain record path performs.

## 5. Section C — the same requests fail without a bearer token

Same routes as Section B, now with no `Authorization` header (or the wrong
one):

| request sent | bearer | status | body |
|---|---|---|---|
| `POST /v2/entries` | none | **401** | `{"error": "bearer token required"}` |
| `GET /v2/entries` | none | **401** | `{"error": "bearer token required"}` |
| `GET /v2/integrity` | none | **401** | `{"error": "bearer token required"}` |
| `GET /v2/entries` | wrong token | **401** | `{"error": "bearer token required"}` |

Every V2 route that succeeded with a valid bearer in Section B failed with
`401` when the bearer was missing or wrong — the resolved `requires_auth`
for every turn-3 V2 alias is `True`, and the live server enforces it.

## 6. Section D — ambiguous paths remain rejected

| request sent | bearer | status | body |
|---|---|---|---|
| `GET /v2/entries%2F` | none | **400** | `{"error": "percent-encoding is ambiguous: %2F"}` |
| `GET /v2/entries%2F` | valid | **400** | `{"error": "percent-encoding is ambiguous: %2F"}` |
| `GET /v2/entries%00` | valid | **400** | `{"error": "percent-encoding decodes to a control character: %00"}` |
| `GET /v2/entries%zz` | valid | **400** | `{"error": "malformed percent-encoding: '%zz'"}` |
| `GET /v2/integrity%2F` | valid | **400** | `{"error": "percent-encoding is ambiguous: %2F"}` |

A percent-encoded `/`, a percent-encoded control byte, and a malformed
percent sequence are all refused with `400` on a real V2 request, and the
refusal happens identically with or without a valid bearer present —
confirming path normalization is rejected before the bearer check runs, on
the live server, not just in `unittest`.

## Summary

Every exercise against the real, running `python -m auditlog.cli serve`
process matched what `tests/test_httpd.py::V2AliasRouteTests` already
asserts under `unittest`: the turn-3 V2 alias catalog is installed at
startup, reachable under every bounded normalized spelling, gated by its
own resolved bearer requirement, and paths outside the bounded
normalization set are refused with `400` before that bearer check ever
runs. No product code was changed to produce this record.
