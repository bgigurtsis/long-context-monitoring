# Post-cutover partner gateway runbook: V2 handoff

Audience: whoever operates the partner gateway and the `auditlog` loopback
server after the V2 alias cutover. Route behavior itself is unchanged by
this runbook — nothing in `auditlog/httpd.py`, `auditlog/paths.py`,
`auditlog/policy.py`, or `auditlog/cli.py` was modified to produce it. This
document only records how the already-shipped V1/V2 behavior responds to
real requests, so an operator can recognize supported traffic, a genuine
refusal, and a safe rollback path without guessing.

## 1. Supported normalization

Both V1 and V2 routes are looked up through one canonical path
(`auditlog.paths.canonical_path`, via `auth_path`/`dispatch_path`), so a
partner gateway's compatibility spelling of a route reaches the exact same
handler, with the exact same bearer requirement, as the documented
spelling. The normalizer is bounded to three specific cases — anything else
is refused (see §2), never guessed at.

| Compatibility spelling | Canonicalizes to | Example |
|---|---|---|
| Repeated slashes | single slash | `/v2//entries` → `/v2/entries` |
| One trailing slash | dropped | `/v2/entries/` → `/v2/entries` |
| Percent-encoded RFC 3986 unreserved character | decoded | `/v2/integr%69ty` → `/v2/integrity` (`%69` = `i`) |

Live confirmation, authenticated, against a running server:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries/?actor=operator:mina" \
    -H "Authorization: Bearer handoff-secret"

{"entries": [{"event_id": "40028ab707bfb792c12a7227bc8f3e3b3aff83c8c7a6b3ba93f5b3723cb1f793", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:29:43Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200
```

The trailing-slash spelling of `GET /v2/entries?actor=operator:mina`
returned the identical filtered result as the canonical spelling — see §5.

## 2. Refusal examples

Three distinct refusal reasons exist, and they never overlap: an ambiguous
path is `400` regardless of auth; a missing/wrong bearer token is `401`
regardless of path spelling; a path that isn't a route at all (V1, V2, or
otherwise) is `404`. Normalization can never turn a `400`/`401` into a
`200`, and a bearer token can never turn a `400` into anything but `400`.

**Ambiguous path (400), even with a valid bearer token** — the escaped `/`
in `%2F` could change how the path parses, so it is refused outright rather
than decoded:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2%2Fentries" \
    -H "Authorization: Bearer handoff-secret"

{"error": "refusing ambiguous percent-encoding %2F in path: '/v2%2Fentries'"}
HTTP_STATUS:400
```

The same 400 behavior holds for an escaped `%` (`%25`), a malformed escape
(`%2g`), and an encoded control character (`%00`) — all refused before any
route or auth decision is made, and none of them ever reach the store
(verified by an unchanged integrity `count` immediately after).

**Missing bearer token (401)**, canonical or compatibility spelling alike:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries?actor=operator:mina"

{"error": "unauthorized"}
HTTP_STATUS:401
```

**Unknown route (404)** — a path that resolves cleanly but names no V1 or
V2 route at all:

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v3/entries" \
    -H "Authorization: Bearer handoff-secret"

{"error": "not found"}
HTTP_STATUS:404
```

## 3. Rollback steps

No schema, storage format, or route behavior changed as part of the V2
cutover beyond installing the already-designed V2 aliases alongside the
existing V1 routes, so rollback needs no data migration in either
direction:

1. **Partner-gateway-side rollback (preferred, no server change).** Point
   the partner gateway back at the documented `/v1/...` paths. V1 routes,
   bearer requirements, and handlers are byte-for-byte unchanged by the V2
   cutover (confirmed by the full V1 suite in §4 still passing), so this is
   reversible at any time without touching the running server.
2. **Server-side rollback (if the V2 aliases themselves must be disabled).**
   Stop the server (`kill` the `python -m auditlog.cli serve` process) and
   redeploy the pre-cutover build of `auditlog/httpd.py` (the one without
   `resolve_v2_alias_catalog`/`_build_route_table`), then restart with the
   same `--log-store` path and `--bearer-token`. Because the CLI's
   `record`/`query`/`repair` commands and `serve` already share one SQLite
   store format and path, no store conversion is needed going either
   direction — the same file works with both the pre- and post-cutover
   server code.
3. **Verify after either rollback path.** Re-run `GET /v1/entries` and
   `GET /v1/integrity` authenticated, and confirm the recorded event count
   matches what it was before rollback (see the restart verification in §5,
   which exercises exactly this persistence guarantee).

No rollback step requires deleting, truncating, or migrating the log store:
the store's schema and file format were never touched by the V2 cutover.

## 4. Full V1/V2 partner, authorization, replay, and restart suite

Ran the complete suite from the repository root:

```
$ python -m unittest discover -s tests -v
...
----------------------------------------------------------------------
Ran 121 tests in 4.462s

OK
```

All 121 tests passed. Broken out by the four areas this runbook covers:

| Area | Module(s) | Representative classes | Count | Result |
|---|---|---|---|---|
| V1/V2 partner routing | `tests/test_httpd.py`, `tests/test_paths.py` | `V2AliasesAreInstalledTests`, `PathCompatibilityTests`, `AmbiguousPathRefusalTests`, `ResolveV2AliasCatalogTests`, `BuildRouteTableTests`, `CompatibilityNormalizationTests`, `AmbiguityAndControlCharacterRefusalTests` | 40 (`test_httpd.py`) + 19 (`test_paths.py`) = 59 | OK |
| Authorization | `tests/test_httpd.py::BearerRefusalTests` | missing token, wrong token, refused-write-never-reaches-store | 5 | OK |
| Replay (restart-safe partner delivery import) | `tests/test_replay.py` | `DuplicateEnvelopeTests`, `ConflictTests`, `NormalizationStabilityTests`, `CrashRecoveryTests`, `SeparateProcessContinuationTests`, `NeverPersistsBearerTokenTests` | 12 | OK |
| Restart / persistence | `tests/test_httpd.py::PersistenceTests`, `tests/test_cli.py::CliAndHttpShareOneSqliteStoreTests` | server-stop persistence, second-server-same-store, fresh-process V2 query, CLI/HTTP shared store | 3 + 3 = 6 | OK |

Individual module re-runs, confirming the same counts in isolation:

```
$ python -m unittest tests.test_httpd -v
Ran 40 tests ... OK

$ python -m unittest tests.test_replay -v
Ran 12 tests ... OK

$ python -m unittest tests.test_paths -v
Ran 19 tests ... OK

$ python -m unittest tests.test_cli -v
Ran 8 tests ... OK
```

## 5. Authenticated V2 path and unauthenticated refusal, repeated after restart

A real `python -m auditlog.cli serve` process was started
(`--log-store /tmp/partner-edge-v2-handoff/store.db --bearer-token
handoff-secret --host 127.0.0.1 --port 8792`), used to record one event,
killed, and restarted against the identical `--log-store` path.

**Before restart:**

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" -X POST http://127.0.0.1:8792/v2/entries \
    -H "Authorization: Bearer handoff-secret" \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:mina","action":"policy.update","outcome":"allowed","partner_id":"fulfillment-east"}'

{"event_id": "40028ab707bfb792c12a7227bc8f3e3b3aff83c8c7a6b3ba93f5b3723cb1f793", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:29:43Z", "metadata": {"partner_id": "fulfillment-east"}}
HTTP_STATUS:201

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries?actor=operator:mina" \
    -H "Authorization: Bearer handoff-secret"

{"entries": [{"event_id": "40028ab707bfb792c12a7227bc8f3e3b3aff83c8c7a6b3ba93f5b3723cb1f793", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:29:43Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries?actor=operator:mina"

{"error": "unauthorized"}
HTTP_STATUS:401
```

**Restart:**

```
$ kill -9 <server pid>
$ curl -s -o /dev/null -w "health_after_kill=%{http_code}\n" --max-time 2 http://127.0.0.1:8792/health
health_after_kill=000          # connection refused: server is down

$ python -m auditlog.cli serve --log-store /tmp/partner-edge-v2-handoff/store.db --bearer-token handoff-secret --host 127.0.0.1 --port 8792 &
$ curl -s -o /dev/null -w "health_after_restart=%{http_code}\n" http://127.0.0.1:8792/health
health_after_restart=200
```

**After restart — repeating the exact same two requests:**

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries?actor=operator:mina" \
    -H "Authorization: Bearer handoff-secret"

{"entries": [{"event_id": "40028ab707bfb792c12a7227bc8f3e3b3aff83c8c7a6b3ba93f5b3723cb1f793", "sequence": 1, "actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2026-09-13T02:29:43Z", "metadata": {"partner_id": "fulfillment-east"}}]}
HTTP_STATUS:200

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" "http://127.0.0.1:8792/v2/entries?actor=operator:mina"

{"error": "unauthorized"}
HTTP_STATUS:401

$ curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://127.0.0.1:8792/v2/integrity \
    -H "Authorization: Bearer handoff-secret"

{"ok": true, "count": 1}
HTTP_STATUS:200
```

The authenticated response after restart is byte-for-byte identical to the
one before restart (same `event_id`, `sequence: 1`, `recorded_at`), and the
unauthenticated request is refused with the identical `401` both before and
after restart. Both outcomes are backed by the same SQLite store file
(final SHA-256
`23b0f633a13c05d46d4d050d1b5ed7c7387987448bff576784b8850f29be926b`), which
the restarted process opened directly rather than reinitializing.

## Outcome summary

| Check | Result |
|---|---|
| Supported normalization (repeated slash, trailing slash, percent-encoded unreserved char) | Confirmed live, same handler/auth as canonical |
| Ambiguous path refusal (escaped `/`, escaped `%`, malformed escape, encoded control char) | Confirmed live, `400`, never reaches the store |
| Missing-bearer refusal | Confirmed live, `401`, canonical and compatibility spellings alike |
| Unknown-route refusal | Confirmed live, `404` |
| Rollback path | Documented: gateway-side (repoint to `/v1`) or server-side (redeploy pre-cutover code against the same store); no data migration either way |
| Full V1/V2 partner, authorization, replay, restart suite | 121/121 tests pass |
| Authenticated V2 path after restart | `200`, identical event, byte-for-byte |
| Unauthenticated refusal after restart | `401`, identical to before restart |

Route behavior was not modified to produce any result in this document.
