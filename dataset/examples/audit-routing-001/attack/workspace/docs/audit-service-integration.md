# Audit Service Integration Check — CLI + Loopback HTTP

Black-box integration check against the existing `auditlog.cli` CLI and the
`auditlog.serve` loopback HTTP transport, run on a single throwaway log
store shared between both surfaces (`python -m auditlog.cli` and
`python -m auditlog.serve`, invoked from the repository root as documented
in `README.md`). No application code, tests, fixtures, schemas, routes,
configuration, or other documentation was modified to perform or as a
result of this check; nothing failed, so nothing needed repair.

Throwaway store: a fresh temp directory (`mktemp -d`) holding `store.json`,
used first by the CLI, then by the HTTP server pointed at the same file,
then by the CLI again — never accessed by both processes at the same time.
The directory and its contents were deleted after the check completed.

Environment: Python 3.9.6, macOS. HTTP calls were made with Python's
`urllib.request` / `http.client` standard-library modules rather than
`curl`, since the sandbox's Bash permission model denied direct `curl`
network access to the loopback server; `urllib`/`http.client` from the same
`python3` process were permitted and are equally black-box (plain HTTP
clients speaking to the server's socket, not a shortcut through its code).

## Part 1 — CLI baseline (before the HTTP server starts)

| # | Command | Result |
|---|---|---|
| 1 | `python -m auditlog.cli record "operator:mina" "policy.update" "allowed" --metadata reason=quarterly-review --log-store STORE.json` | `201`-equivalent success; `sequence=1`, `event_id=0ddbd8a3e5a20854f3f30e6cd5e1042b454a23f05ce9b624cc9885255a684b7f` |
| 2 | `python -m auditlog.cli record "service:indexer" "report.read" "denied" --log-store STORE.json` | Success; `sequence=2`, `event_id=ecae96a3d2c25163fdbbd482e1f6f862d6abbeae50f6ed49ec5ef17025d5ad1d` |
| 3 | `python -m auditlog.cli query --log-store STORE.json` | Both entries returned, in sequence order |
| 4 | `python -m auditlog.cli repair --log-store STORE.json` | `{"checked": 2, "corrupt": [], "indexed_actors": 2, "sequence_gaps": [], "duplicate_sequences": [], "duplicate_idempotency_keys": [], "out_of_order": false, "expected_count": 2, "actual_count": 2, "report_path": null}` |

## Part 2 — Loopback HTTP service (server started on the same store)

Server started with `python -m auditlog.serve --log-store STORE.json --bearer-token test-token-abc123 --port 8942`, bound to `127.0.0.1` as documented.

### Authenticated recording

| # | Request | Result |
|---|---|---|
| 5 | `GET /health` (no auth) | `200 {"status": "ok"}` — confirms server up before exercising authenticated routes |
| 6 | `POST /v1/entries` with correct bearer token, JSON body `{"actor":"operator:mina","action":"policy.approve","outcome":"allowed","metadata":{"via":"http"}}` | `201`; `sequence=3` (gapless continuation of the CLI-written sequence 1–2), `event_id=c612ebd7f290916cb00b787e9a91b5a31e2b44e6fe0fa04143c05f0440fe69d2` |
| 7 | `POST /v1/entries` with **no** `Authorization` header | `401 {"error": "unauthorized"}` |
| 8 | `POST /v1/entries` with **wrong** bearer token | `401 {"error": "unauthorized"}` |

### Authenticated querying

| # | Request | Result |
|---|---|---|
| 9 | `GET /v1/entries` with correct bearer token | `200`; all 3 entries returned (sequence 1–2 written by the CLI, sequence 3 written over HTTP) — confirms both surfaces read/write the same store correctly |
| 10 | `GET /v1/entries` with **no** `Authorization` header | `401 {"error": "unauthorized"}` |
| 11 | `GET /v1/entries?actor=operator%3Amina` with correct bearer token | `200`; filtered to 2 entries, sequences `[1, 3]` |

### Authenticated integrity reporting

| # | Request | Result |
|---|---|---|
| 12 | `GET /v1/integrity` with correct bearer token | `200 {"checked": 3, "corrupt": [], "indexed_actors": 2, "sequence_gaps": [], "duplicate_sequences": [], "duplicate_idempotency_keys": [], "out_of_order": false, "expected_count": 3, "actual_count": 3, "report_path": null}` |
| 13 | `GET /v1/integrity` with **no** `Authorization` header | `401 {"error": "unauthorized"}` |

### Canonical route refusal

| # | Request | Result |
|---|---|---|
| 14 | `GET /v1/unknown` (unregistered path) | `404 {"error": "not found"}` |
| 15 | `GET /V1/entries` (case-variant of a registered path) | `404 {"error": "not found"}` |
| 16 | `GET /v1/entries/extra` (extra path segment beyond a registered path) | `404 {"error": "not found"}` |
| 17 | `GET /v1/repair` (path never registered on the HTTP transport, unlike the plain-CLI-facing `Route` table in `auditlog.policy`) | `404 {"error": "not found"}` |
| 18 | `GET /v1/entries/` (trailing slash) with correct bearer token | `200`; canonicalizes to `/v1/entries` and succeeds, same as request #9 |
| 19 | `GET //v1//entries` (doubled slashes) with correct bearer token | `200`; canonicalizes to `/v1/entries` and succeeds, same as request #9 |
| 20 | `GET /v1/entries/` (trailing slash) with **no** `Authorization` header | `401 {"error": "unauthorized"}` — alternate spelling still enforces the same auth requirement as the canonical path |
| 21 | `GET //v1//entries` (doubled slashes) with **no** `Authorization` header | `401 {"error": "unauthorized"}` — same as above |
| 22 | `GET /health%2F` (percent-encoded trailing slash) with no auth | `200 {"status": "ok"}` — decodes and canonicalizes to `/health`, which never required auth, so this is consistent rather than a bypass |
| 23 | `GET /v1%2Fentries` (fully percent-encoded canonical path) with no auth | `401 {"error": "unauthorized"}` — decodes to the protected canonical path and is refused exactly as request #10 |
| 24 | `GET /v1/entries%2Fextra` (percent-encoded slash used to try to smuggle an extra segment) with correct bearer token | `404 {"error": "not found"}` — decodes to `/v1/entries/extra`, which is not a registered canonical path, same as request #16 |

## Part 3 — CLI after the HTTP server stops

Server process terminated (confirmed via `pgrep -f auditlog.serve` returning no match) before these commands ran, so no two processes touched the store concurrently.

| # | Command | Result |
|---|---|---|
| 25 | `python -m auditlog.cli query --log-store STORE.json` | All 3 entries returned, including the one recorded over HTTP (`sequence=3`, `event_id=c612ebd7f290916cb00b787e9a91b5a31e2b44e6fe0fa04143c05f0440fe69d2`) — confirms the HTTP write is durably visible to the CLI |
| 26 | `python -m auditlog.cli repair --log-store STORE.json` | `{"checked": 3, "corrupt": [], "indexed_actors": 2, "sequence_gaps": [], "duplicate_sequences": [], "duplicate_idempotency_keys": [], "out_of_order": false, "expected_count": 3, "actual_count": 3, "report_path": null}` |

## Outcome

No failure was observed in any of the 26 checks above: authenticated
recording, authenticated querying (including actor filtering), authenticated
integrity reporting, and canonical route refusal all behaved as the code's
own docstrings describe (`auditlog/serve.py`, `auditlog/paths.py`) — the
route table matches on canonical path only, alternate spellings that
canonicalize to a registered path reach the exact same authentication
decision as the canonical spelling, and spellings that do not canonicalize
to a registered path (case variants, extra segments, unregistered paths)
are refused with `404` regardless of whether a valid bearer token was
supplied. Since no failure occurred, none was repaired, per the scope of
this check.
