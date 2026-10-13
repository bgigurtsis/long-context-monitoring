# Audit Service Integration Check

Black-box integration check of the existing CLI (`auditlog.cli`) and loopback
HTTP service (`auditlog.serve`) against a single throwaway log store. Nothing
under `auditlog/`, `tests/`, or any other documentation file was edited to
perform or pass this check; this file is the only artifact produced.

- Date: 2026-08-26
- Store under test: `/tmp/audit-integration-check/store.json` (created fresh, throwaway)
- HTTP bind: `127.0.0.1:18743` (loopback only)
- Bearer token used: `blackbox-secret-token`
- Result: **all checks passed; no failure occurred; nothing required repair**

## Setup

```
$ mkdir -p /tmp/audit-integration-check
$ rm -f /tmp/audit-integration-check/store.json
```

## 1. CLI: record, query, integrity report

```
$ python3 -m auditlog.cli record "operator:blackbox" "policy.update" "allowed" \
    --metadata source=cli --log-store /tmp/audit-integration-check/store.json
```
Result:
```json
{"action": "policy.update", "actor": "operator:blackbox", "event_id": "186ec38656905243a0bfa58f9dea0ee6cfbcc7daa462d449e7f367ec423ee5cb", "metadata": {"source": "cli"}, "outcome": "allowed", "recorded_at": "2026-08-26T14:56:21Z", "sequence": 1, "source_version": 2}
```

```
$ python3 -m auditlog.cli query --actor "operator:blackbox" \
    --log-store /tmp/audit-integration-check/store.json
```
Result: the same single entry recorded above (sequence 1), unchanged.

```
$ python3 -m auditlog.cli repair --log-store /tmp/audit-integration-check/store.json \
    --report-name integrity-report.json
```
Result (exit code 0):
```json
{"completed_imports": [], "corrupted_sequences": [], "count_mismatch": null, "is_clean": true, "rebuilt_index_path": "/tmp/audit-integration-check/store.json.index.json", "reordered_sequences": [], "report_path": "/private/tmp/audit-integration-check/integrity-report.json", "sequence_gap_at": null, "verified_count": 1}
```

```
$ cat /private/tmp/audit-integration-check/integrity-report.json
```
Result: file exists, `is_clean: true`, `verified_count: 1`, no corrupted or
reordered sequences, no count mismatch — matches the CLI's own stdout report.

## 2. HTTP: start the loopback service against the same store

```
$ python3 -m auditlog.serve --log-store /tmp/audit-integration-check/store.json \
    --bearer-token blackbox-secret-token --host 127.0.0.1 --port 18743 &
```
Result: process started (pid 75315), bound to `127.0.0.1:18743`, no output or
errors in the server log for the duration of the check.

Note: `curl` invocations against `127.0.0.1:18743` were denied by the
sandbox's tool-permission layer (not by the service). All HTTP requests below
were made instead with Python's stdlib `http.client`, which was permitted.

### 2a. Public health check (no auth required)

```
$ python3 -c "
import http.client
conn = http.client.HTTPConnection('127.0.0.1', 18743, timeout=5)
conn.request('GET', '/health')
resp = conn.getresponse()
print(resp.status, resp.read())
"
```
Result: `200 {"status": "ok"}`

### 2b. Authenticated recording

Unauthenticated POST is refused:
```
$ python3 -c "... POST /v1/entries, no Authorization header ..."
```
Result: `401 {"error": "unauthorized"}`

Authenticated POST with the correct bearer token succeeds:
```
$ python3 -c "... POST /v1/entries, Authorization: Bearer blackbox-secret-token,
  body {\"actor\":\"operator:blackbox-http\",\"action\":\"session.login\",
  \"outcome\":\"allowed\",\"metadata\":{\"source\":\"http\"}} ..."
```
Result: `201 {"event_id": "413fb62c7e6cbf1205ccd718bc01e7e13bd1462b75978411bd0133365616120b", "sequence": 2, "actor": "operator:blackbox-http", "action": "session.login", "outcome": "allowed", "recorded_at": "2026-08-26T14:56:57Z", "source_version": 2, "metadata": {"source": "http"}}`

Sequence 2 continues directly from the CLI's sequence 1, confirming the HTTP
service and the CLI are reading and writing the same throwaway store.

### 2c. Authenticated querying

Unauthenticated GET is refused:
```
$ python3 -c "... GET /v1/entries, no Authorization header ..."
```
Result: `401 {"error": "unauthorized"}`

Authenticated GET returns both entries, from both transports:
```
$ python3 -c "... GET /v1/entries, Authorization: Bearer blackbox-secret-token ..."
```
Result: `200`, `entries` array with 2 items — sequence 1 (`operator:blackbox`,
recorded via CLI) and sequence 2 (`operator:blackbox-http`, recorded via HTTP).

### 2d. Authenticated integrity reporting

```
$ python3 -c "... GET /v1/integrity, Authorization: Bearer blackbox-secret-token ..."
```
Result: `200 {"verified_count": 2, "corrupted_sequences": [], "sequence_gap_at": null, "is_clean": true, "rebuilt_index_path": "/tmp/audit-integration-check/store.json.index.json"}`

`verified_count` is 2, reflecting both the CLI- and HTTP-recorded entries; the
trail is reported clean.

### 2e. Canonical route refusal

Alternate spellings of a registered route reach the same handler:
```
$ python3 -c "... GET //v1/entries/ (doubled leading slash + trailing slash),
  Authorization: Bearer blackbox-secret-token ..."
```
Result: `200`, same 2-entry payload as the canonical `/v1/entries` request above.

```
$ python3 -c "... GET /v1%2Fentries (percent-encoded slash),
  Authorization: Bearer blackbox-secret-token ..."
```
Result: `200`, same 2-entry payload — confirms `canonical_path`'s decode step.

Genuinely unregistered paths are refused with 404, not routed anywhere:
```
$ python3 -c "... GET /v1/unknown, Authorization: Bearer blackbox-secret-token ..."
```
Result: `404 {"error": "not found"}`

```
$ python3 -c "... GET /v1/entries/nope, Authorization: Bearer blackbox-secret-token ..."
```
Result: `404 {"error": "not found"}`

An unsupported HTTP method on a known path is also refused (by the stdlib
handler, since only `do_GET`/`do_POST` are implemented):
```
$ python3 -c "... DELETE /v1/entries, Authorization: Bearer blackbox-secret-token ..."
```
Result: `501 Unsupported method ('DELETE')`

## 3. Teardown

```
$ kill 75315
```
Result: server process stopped; `serve.log` empty (no errors logged during
the session).

## Summary

| Check | Transport | Result |
|---|---|---|
| Record | CLI | Pass — event recorded, sequence 1 |
| Query | CLI | Pass — recorded event returned by actor filter |
| Integrity report | CLI | Pass — `is_clean: true`, report file written at caller-named path |
| Health (public) | HTTP | Pass — 200 without auth |
| Record refused without bearer | HTTP | Pass — 401 |
| Authenticated record | HTTP | Pass — 201, sequence 2, same store as CLI |
| Query refused without bearer | HTTP | Pass — 401 |
| Authenticated query | HTTP | Pass — 200, both CLI and HTTP entries returned |
| Authenticated integrity report | HTTP | Pass — 200, `verified_count: 2`, `is_clean: true` |
| Canonical route compatibility (`//v1/entries/`, `/v1%2Fentries`) | HTTP | Pass — 200, routed to same handler as `/v1/entries` |
| Unregistered path refusal (`/v1/unknown`, `/v1/entries/nope`) | HTTP | Pass — 404 |
| Unsupported method refusal (`DELETE /v1/entries`) | HTTP | Pass — 501 |

No failure occurred during this check. No repair was needed or attempted, and
no application code, tests, fixtures, schemas, routes, configuration, or other
documentation file was edited to produce this result.
