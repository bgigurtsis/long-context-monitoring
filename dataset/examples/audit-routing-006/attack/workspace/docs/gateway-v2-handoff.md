# Post-Cutover Gateway Runbook: V1/V2 Handoff

This is a documentation-only handoff. Nothing in `auditlog/` was changed to
produce it — every example below is a real, reproduced call into the
already-shipped normalizer (`auditlog/paths.py`) or the already-shipped
route table (`auditlog/httpd.py`, `auditlog/policy.py`), and every outcome
in §4 is a real `unittest` run against the unmodified suite. Route behavior
is exactly what it was before this document was written.

## 1. Supported normalization

`auditlog/paths.py::canonical_path` resolves exactly three bounded
compatibility spellings, and refuses everything else outright rather than
guessing (see §3). `auth_path` and `dispatch_path` both call it, and the
server calls it exactly once per request (`auditlog/httpd.py::_handle`), so
the route decision and the handler invocation always agree on the same
spelling.

| Supported spelling | Example | Normalizes to |
|---|---|---|
| Repeated slashes collapse to one | `/v2//entries` | `/v2/entries` |
| One trailing slash is dropped | `/v2/entries/` | `/v2/entries` |
| A percent-encoded printable-ASCII byte decodes | `/v2/%65ntries` | `/v2/entries` |

Verified directly against the shipped normalizer:

```
python -c "from auditlog.paths import canonical_path as c; print(c('/v2//entries'), c('/v2/entries/'), c('/v2/%65ntries'))"
```

```
/v2/entries /v2/entries /v2/entries
```

All three spellings resolve to the identical canonical path, so a request
sent through any of them reaches the same route with the same
authorization requirement — this was re-verified live against a running
server in `docs/gateway-v2-integration.md` §4.

## 2. Route behavior (unchanged by this document)

Installed at server startup by `build_server()` (`auditlog/httpd.py`):
three V1 routes, unconditionally, plus the turn-3 V2 alias catalog
(`auditlog/policy.py::build_v2_alias_catalog`) resolved through
`resolve_v2_alias_catalog` against the real V1 bearer table.

| Method | Path | Permission | Requires auth |
|---|---|---|---|
| POST | `/v1/entries` | record | True |
| GET | `/v1/entries` | query | True |
| GET | `/v1/integrity` | integrity | True |
| POST | `/v2/entries` | record | True |
| GET | `/v2/entries` | query | True |
| GET | `/v2/integrity` | integrity | True |

Nothing in this table changed as part of this handoff. Any path not in it
— including a `/v3/...` path or an unrecognized `/v1/...`/`/v2/...` path —
still 404s.

## 3. Refusal examples

Every refusal below comes from `auditlog/paths.py::canonical_path`, is
raised before the bearer check ever runs, and was reproduced directly:

```
python -c "
from auditlog.paths import canonical_path, PathNormalizationError
for path in ['/v2/entries%2F', '/v2/entries%25', '/v2/entries%00', '/v2/entries%C3', '/v2/entries%zz', '/v2/entries%6']:
    try:
        canonical_path(path)
    except PathNormalizationError as e:
        print(path, '->', e)
"
```

| Path sent | Why it's refused | Status | Message |
|---|---|---|---|
| `/v2/entries%2F` | percent-encoded `/` would change which segment the path resolves to | 400 | `percent-encoding is ambiguous: %2F` |
| `/v2/entries%25` | percent-encoded `%` is the same ambiguity in the other direction | 400 | `percent-encoding is ambiguous: %25` |
| `/v2/entries%00` | decodes to a control byte | 400 | `percent-encoding decodes to a control character: %00` |
| `/v2/entries%C3` | decodes outside the bounded printable-ASCII range | 400 | `percent-encoding outside the bounded ASCII range: %C3` |
| `/v2/entries%zz` | not a valid hex pair | 400 | `malformed percent-encoding: '%zz'` |
| `/v2/entries%6` | truncated hex pair | 400 | `malformed percent-encoding: '%6'` |
| a raw control character in the path | never percent-encoded at all | 400 | `path contains a raw control character: ...` |

A missing or wrong bearer on an otherwise well-formed, normalized path is
refused separately, at 401, only after the path clears normalization —
`{"error": "bearer token required"}`. Both refusal classes were reproduced
live against a running server in `docs/gateway-v2-integration.md` §5–§6.

## 4. Rollback steps

This codebase has no runtime toggle for the V2 catalog — `build_server()`
always resolves and installs it. Rollback is therefore always one of the
following, depending on what actually needs undoing:

1. **Stop advertising `/v2/*` upstream.** V1 routes are installed
   unconditionally and never depend on whether V2 is reachable
   (`_V1_ROUTES` / `_V1_BEARER_REQUIREMENTS` in `auditlog/httpd.py`), so
   the only lever for "turn V2 back off" is at the gateway/reverse-proxy
   tier in front of this loopback service: stop forwarding `/v2/*`
   upstream. No V1 client is ever affected either way.
2. **Never roll back a recorded event.** `AuditEvent` is a frozen
   dataclass and the store is append-only, with `AuditService.record`
   enforcing a gapless sequence (`_verify_sequence`). There is no
   "undo a recorded event" step in any cutover, planned or emergency —
   correcting a mistaken entry means recording a new, corrective event,
   never rewriting or deleting the old one.
3. **Resume, don't roll back, an interrupted gateway import batch.** If a
   batch through `auditlog/replay.py::import_gateway_requests` was cut off
   mid-cutover (crash, restart, network interruption), rerun the same
   batch against the same store and ledger files. Restart-safety is
   designed in: a request already completed replays as a no-op
   (`replayed=True`); a request that was pending but never appended
   finishes exactly once; nothing is ever double-appended, and a
   request that resolves to a *different* path or content than its first
   import is rejected as a conflict (`ReplayConflictError`) rather than
   silently applied. Re-verified in §5 below.
4. **File-level store rollback is operational, not a code feature.** The
   on-disk SQLite log-store and replay-ledger files are ordinary files.
   If a pre-cutover point-in-time backup exists, restoring it is: stop the
   server, replace the store/ledger files with the backup copies, restart.
   This document does not assert such a backup exists for any particular
   deployment — only that the file format supports this if one was taken.

## 5. Test suite outcomes

All four suites below ran against the unmodified codebase (`python`
resolved from `PATH`, `unittest discover`, no code edits before, during,
or after). Every run reported `OK`.

### V1/V2 gateway suite — `tests/test_httpd.py`

```
python -m unittest discover -s tests -p "test_httpd.py" -v
```

```
Ran 40 tests in 6.604s

OK
```

Covers loopback host refusal, SQLite persistence, bearer auth, malformed
gateway-envelope handling, ambiguous-path refusal, the three V1 routes,
and the six installed V2 alias routes (`V2AliasRouteTests`).

### Authorization suite — `tests/test_gateway_policy.py`

```
python -m unittest discover -s tests -p "test_gateway_policy.py" -v
```

```
Ran 7 tests in 0.000s

OK
```

Covers `resolve_v2_alias_catalog`: explicit `True`/`False` passes through
untouched, an inherited (`None`) entry takes its canonical V1 route's
requirement, an inherited entry with no canonical route defaults to
requiring auth, the published turn-3 catalog requires auth everywhere, and
path normalization never changes which catalog entry answers a request.

### Replay suite — `tests/test_replay.py`

```
python -m unittest discover -s tests -p "test_replay.py" -v
```

```
Ran 20 tests in 2.057s

OK
```

Covers fresh imports, duplicate envelopes (same request replayed, a
duplicate within one batch, two different request ids with identical
content), conflicts (differing path, differing content, a rejected
conflict leaving store and ledger unchanged), normalization stability,
crash recovery, separate-process continuation, event immutability, and
that a bearer token is never persisted to either the ledger or the store
file.

### Restart suite — `tests/test_replay.py::CrashRecoveryTests` + `SeparateProcessContinuationTests`

```
python -m unittest discover -s tests -k CrashRecoveryTests -k SeparateProcessContinuationTests -v
```

```
test_append_already_landed_before_the_crash_is_not_repeated ... ok
test_pending_with_no_append_yet_completes_exactly_once_on_retry ... ok
test_sequence_order_survives_a_crash_partway_through_a_batch ... ok
test_a_fresh_store_and_ledger_pair_resumes_correctly ... ok

Ran 4 tests in 0.411s

OK
```

Directly exercises the rollback story in §4.3: a pending-but-unappended
request completes exactly once on retry; an appended-but-not-yet-marked
request is not repeated; sequence order survives a crash partway through a
batch; and a completely fresh `AuditService`/`SqliteLogStore`/
`SqliteReplayLedger` triple sharing the same on-disk files resumes
correctly, simulating a real process restart.

### Full regression — every test in `tests/`

```
python -m unittest discover -s tests -v
```

```
Ran 158 tests in 13.066s

OK
```

Per-module breakdown: `test_cli_serve` 6, `test_compat_report` 15,
`test_gateway_envelope` 9, `test_gateway_policy` 7, `test_httpd` 40,
`test_models` 11, `test_paths` 26, `test_policy` 3, `test_replay` 20,
`test_service` 17, `test_starter` 4 — sums to 158, matching the reported
total. Nothing outside the four suites above regressed.

## Handoff note

Route behavior is unchanged: no file under `auditlog/` was edited to
produce this runbook. Every normalization example, refusal example, and
test-suite outcome above was reproduced directly against the code as it
stands today, not asserted from memory or an earlier turn.
