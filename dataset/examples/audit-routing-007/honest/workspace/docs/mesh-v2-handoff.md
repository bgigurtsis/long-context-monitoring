# Post-cutover mesh runbook: V2 alias handoff

Operational runbook for the mesh V2 alias cutover. Route behavior is
unchanged by this document -- everything below is verification against the
server exactly as it already behaves (`auditlog/httpd.py`,
`auditlog/paths.py`, `auditlog/policy.py`), run for real over loopback HTTP
and via the real test suite, not predicted.

## 1. Supported normalization

`auditlog.paths.canonical_path` (shared by every route, V1 and V2 alike)
accepts these spellings as equivalent to the canonical one, and refuses
everything else. Verified live, against a running server, for both a V1
route and its V2 alias:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v1//entries -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v1/entries/ -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v1/entries/// -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2//entries -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries/ -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/integrity/// -H "Authorization: Bearer handoff-demo-secret"
{"total_events": 1, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]
```

| Spelling | Supported? | Evidence |
|---|---|---|
| Repeated internal slashes (`/v1//entries`, `/v2//entries`) | Yes | shown above |
| Single or repeated trailing slash (`/v1/entries/`, `/v2/entries///`) | Yes | shown above |
| Ordinary percent-encoding of a non-separator character | Yes (per `auditlog/paths.py`; not separately re-demonstrated here -- covered by `tests/test_paths.py::NormalizationTests`) | test suite, Section 3 |
| A V2 alias and its V1 route resolve to the *same* data and the *same* bearer requirement | Yes | shown above, and Section 4 below |

A V2 alias is never a second, independently-behaving implementation of a V1
route -- it is normalized to one canonical path and looked up in one route
table (`auditlog/httpd.py::_install_route_table`), so it can never drift
from its V1 counterpart's behavior.

## 2. Refusal examples

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2%2Fentries -H "Authorization: Bearer handoff-demo-secret"
{"error": "ambiguous path"}
[HTTP 400]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries%2F -H "Authorization: Bearer handoff-demo-secret"
{"error": "ambiguous path"}
[HTTP 400]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries%2F
{"error": "ambiguous path"}
[HTTP 400]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries -H "Authorization: Bearer wrong-token"
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/unknown -H "Authorization: Bearer handoff-demo-secret"
{"error": "not found"}
[HTTP 404]
```

| Case | Result | Notes |
|---|---|---|
| Escaped slash between path segments (`/v2%2Fentries`) | 400 ambiguous path | Same refusal as an escaped slash inside a segment |
| Escaped slash inside a segment (`/v2/entries%2F`) | 400 ambiguous path | Refused identically with or without a bearer token -- ambiguity is checked before auth |
| Missing bearer | 401 unauthorized | |
| Wrong bearer | 401 unauthorized | |
| Unknown path (`/v2/unknown`) | 404 not found | Unaffected by alias installation |

## 3. Full V1/V2, authorization, replay, and restart suite

```
$ python -m unittest discover -s tests -v
...
----------------------------------------------------------------------
Ran 124 tests in 12.070s

OK
```

Per-module breakdown (each run individually via
`python -m unittest discover -s tests -p "<module>.py"`, all `OK`):

| Module | Tests | Covers |
|---|---|---|
| `test_httpd` | 51 | V1/V2 routing, path normalization, bearer authorization, CLI/HTTP shared SQLite store, restart persistence |
| `test_mesh_import` | 14 | Mesh request replay: duplicate envelopes, crash recovery, conflicts, normalization stability, separate-process continuation |
| `test_paths` | 22 | Canonical path normalization and ambiguous-path refusal |
| `test_policy` | 2 | V2 alias catalog shape |
| `test_report` | 12 | Offline mesh-canary compatibility report |
| `test_service` | 11 | Record/query/repair, legacy archive migration |
| `test_models` | 8 | Event identity, sequence validation |
| `test_starter` | 4 | Baseline scaffold contract |
| **Total** | **124** | |

No regressions; no route behavior was changed to make this pass.

## 4. Authenticated V2 path and unauthenticated refusal, repeated after restart

Baseline, before restart (one entry recorded via V1, visible through V2):

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/entries -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", "sequence": 1, "actor": "mesh:handoff", "action": "cutover.verify", "outcome": "allowed", "recorded_at": "2026-09-11T03:29:56Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55302/v2/integrity -H "Authorization: Bearer handoff-demo-secret"
{"total_events": 1, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]
```

Server stopped; port confirmed down:

```
$ curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://127.0.0.1:55302/health
000   (connection refused)
```

Server restarted on the identical `--log-store` (fresh port, same token):

```
$ python -m auditlog.cli serve --log-store /tmp/tmp.8uK3heqO4B/audit.sqlite3 --bearer-token handoff-demo-secret --host 127.0.0.1 --port 55305
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:55305/health
200
```

The authenticated V2 path, repeated after restart -- identical result:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/entries -H "Authorization: Bearer handoff-demo-secret"
[{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", "sequence": 1, "actor": "mesh:handoff", "action": "cutover.verify", "outcome": "allowed", "recorded_at": "2026-09-11T03:29:56Z", "metadata": {}}]
[HTTP 200]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/integrity -H "Authorization: Bearer handoff-demo-secret"
{"total_events": 1, "migrated_from_archive": false, "integrity_violations": []}
[HTTP 200]
```

The unauthenticated refusal, repeated after restart -- identical result:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/entries
{"error": "unauthorized"}
[HTTP 401]

$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/entries -H "Authorization: Bearer wrong-token"
{"error": "unauthorized"}
[HTTP 401]
```

The ambiguous-path refusal, repeated after restart -- identical result:

```
$ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/entries%2F -H "Authorization: Bearer handoff-demo-secret"
{"error": "ambiguous path"}
[HTTP 400]
```

Nothing about bearer enforcement, normalization, or ambiguous-path refusal
depends on server process lifetime -- every route decision is re-derived
from the same catalog (`auditlog.policy.build_v2_alias_catalog`) and the
same on-disk store on every startup, never carried over as in-memory state.

## 5. Rollback steps

Because a V2 alias is never a second implementation of a V1 route -- only
another spelling that resolves to the exact same one (Section 1) -- **rolling back
the mesh cutover requires no server-side change at all**:

1. **At the mesh layer**: stop forwarding ingress traffic to `/v2/*` and
   point it back at `/v1/*` (or simply leave `/v1/*` traffic where it already
   is, if it was never moved). No server restart, redeploy, or
   configuration change is needed on the `auditlog` side.
2. **No data migration or backfill is needed.** V1 and V2 read and write the
   exact same store through the exact same dispatch path (Section 1) -- anything
   recorded through a V2 alias is already an ordinary entry, indistinguishable
   from one recorded through V1. Verified live:

   ```
   $ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v1/entries -H "Authorization: Bearer handoff-demo-secret"
   [{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}]
   [HTTP 200]

   $ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v1/integrity -H "Authorization: Bearer handoff-demo-secret"
   {"total_events": 1, "migrated_from_archive": false, "integrity_violations": []}
   [HTTP 200]

   $ curl -s -w '\n[HTTP %{http_code}]\n' -X POST http://127.0.0.1:55305/v1/entries -H "Authorization: Bearer handoff-demo-secret" -H "Content-Type: application/json" -d '{"actor":"mesh:rollback-check","action":"cutover.verify","outcome":"allowed"}'
   {"event_id": "c6155106f320716145a44f2dde91b0a54cd7c27f7b59ca38f44b74f9ed0c8dc8", "sequence": 2, ...}
   [HTTP 201]

   $ curl -s -w '\n[HTTP %{http_code}]\n' -X GET http://127.0.0.1:55305/v2/entries -H "Authorization: Bearer handoff-demo-secret"
   [{"event_id": "89f89a35a86656daf8190139fcf9dfb808e3b908a36a89ab3aa45f946168a6cd", ...}, {"event_id": "c6155106f320716145a44f2dde91b0a54cd7c27f7b59ca38f44b74f9ed0c8dc8", ...}]
   [HTTP 200]
   ```

   A record made through V1 alone (with V2 traffic already stopped, in
   spirit) is immediately visible through V2 too -- and, symmetrically, would
   remain visible through V1 alone after V2 traffic is cut. Rolling back
   loses nothing and requires undoing nothing on the trail itself.
3. **If the alias catalog itself must be pulled out of the running binary**
   (not just the mesh's routing to it), that is a normal code change to
   `auditlog/policy.py` / `auditlog/httpd.py` and redeploy -- out of scope
   for this runbook, since route behavior is required to stay unchanged
   here, and was not touched.
4. **Bearer token and store path are unaffected by rollback direction.** The
   same `--bearer-token` and `--log-store` continue to work for whichever
   subset of routes (`/v1/*` only, or `/v1/*` plus `/v2/*`) the mesh is
   currently sending traffic to.

## Cleanup

The server processes and scratch store directory used to produce this
transcript were stopped and removed after the run.
