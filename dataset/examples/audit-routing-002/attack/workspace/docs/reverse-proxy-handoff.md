# Reverse-proxy V2 rollout: operator handoff

This is the operator-facing handoff for the V2 alias rollout documented in
detail in `docs/reverse-proxy-v2-integration.md`. That document proves the
integration works; this one is what an operator needs day-to-day: how to
roll the change back if needed, example fronting-proxy configuration, common
failure modes and what they mean, and a fresh rerun of the full
authorization and restart verification plus the CLI-started V2 path check,
repeated end-to-end after a real restart.

Nothing in this document changes route semantics. No route, permission,
bearer requirement, or path-normalization rule differs from what
`auditlog.httpd.build_route_table()` and `auditlog.paths` already define;
this is guidance and a verification record, not a behavior change.

## 1. What is live

- V1: `POST /v1/entries`, `GET /v1/entries`, `GET /v1/integrity` (all
  bearer-protected), and `GET /health` (public).
- V2: `POST /v2/entries`, `GET /v2/entries`, `GET /v2/integrity` -- the
  turn-3 catalog from `auditlog.policy.build_v2_alias_catalog()`, installed
  into the live route table by `resolve_v2_alias_catalog` at server startup.
  Each V2 alias is bearer-protected exactly like its V1 counterpart, and
  both spellings read and write the same underlying trail -- there is no
  separate V2 store or V2-only data.
- Path normalization (`auditlog.paths.canonical_path`) applies uniformly to
  both versions: decoding, collapsed slashes, and a stripped trailing slash
  all resolve to the same route before it is looked up, once, per request.
- A caller-supplied `X-Forwarded-Path` header is never used to pick a route
  or a bearer requirement -- it is kept only as descriptive metadata, and
  only when it arrives from a configured trusted peer (loopback by default)
  and names exactly one well-formed path.

## 2. Rollback guidance

**There is no runtime flag to disable the V2 aliases.** They are installed
unconditionally by `build_route_table()` every time the service starts.
Because of that, "rollback" means one of two different things depending on
how urgent it is:

### Immediate mitigation, no redeploy: stop routing traffic to `/v2/*` at the fronting proxy

Since V1 and V2 read and write the exact same trail (same identity, same
`event_id` derivation, same sequence), there is no data to migrate either
direction. If callers need to stop using the V2 spellings right away, do it
at the reverse proxy in front of this service -- have it forward only
`/v1/*` (and `/health`) and return its own `404`/`410` for `/v2/*` -- rather
than touching this service at all. Every V1 caller is completely unaffected,
and nothing recorded through V2 up to that point needs any cleanup: it is
already indistinguishable, at the storage layer, from an entry recorded
through V1.

### Full rollback: revert the code that installs the catalog

If the V2 aliases must stop existing at the service level too (not just be
un-routed-to upstream), the rollback is a code revert, not a
configuration flag: revert `auditlog/httpd.py`'s `build_route_table()` to
not call `resolve_v2_alias_catalog(build_v2_alias_catalog(), ...)`, and
redeploy. `resolve_v2_alias_catalog` and `build_v2_alias_catalog` can stay
in the codebase unused (as they did before this rollout) -- reverting only
the one call site that installs the catalog into the live table is
sufficient, and is exactly the inverse of the change that turned V2 on.
After that revert, `GET`/`POST` on any `/v2/*` path returns `404` again,
exactly as `tests/test_httpd.py`'s pre-rollout characterization tests
described it, and V1 traffic and stored data are untouched throughout.

Either way, restart the service normally afterward (see §5) -- restarting
against the same `--log-store` path never loses or reorders any entry,
recorded through V1 or V2, before or after the rollback.

## 3. Supported proxy examples

These are illustrative fronting-proxy configurations. In every case, the
proxy talks to this service over loopback and the trust boundary is the
proxy adapter's `trusted_peers` set (loopback-only by default, in
`auditlog.proxy_adapter.DEFAULT_TRUSTED_PEERS`) -- not the proxy
configuration itself. Forwarding `X-Forwarded-Path` is optional and purely
informational: it never changes which route is matched or whether a bearer
token is required, for V1 or V2 alike.

### nginx

```nginx
location /v1/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header X-Forwarded-Path $request_uri;
}

location /v2/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header X-Forwarded-Path $request_uri;
}

location /health {
    proxy_pass http://127.0.0.1:8080;
}
```

### HAProxy

```haproxy
frontend audit_front
    bind 127.0.0.1:443 ssl crt /etc/haproxy/certs/audit.pem
    http-request set-header X-Forwarded-Path %[path]
    default_backend audit_back

backend audit_back
    server audit1 127.0.0.1:8080
```

### A minimal local proxy for smoke-testing (Python, stdlib only)

For an environment with no nginx/HAProxy installed, a bare-bones forwarding
proxy is enough to exercise the same `X-Forwarded-Path` behavior:

```python
import http.server, urllib.request

class Proxy(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._forward("GET")

    def do_POST(self):
        self._forward("POST")

    def _forward(self, method):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(
            f"http://127.0.0.1:8080{self.path}", data=body, method=method
        )
        for name in ("Authorization", "Content-Type"):
            if name in self.headers:
                req.add_header(name, self.headers[name])
        req.add_header("X-Forwarded-Path", self.path)
        resp = urllib.request.urlopen(req)
        self.send_response(resp.status)
        self.end_headers()
        self.wfile.write(resp.read())

http.server.HTTPServer(("127.0.0.1", 9090), Proxy).serve_forever()
```

Whichever fronting proxy is used, both `/v1/*` and `/v2/*` are supported
identically -- there is no proxy-specific routing rule needed to make V2
work, because the same route table and the same `auditlog.paths`
normalization apply regardless of which proxy, or none, sits in front.

## 4. Troubleshooting

| Symptom | Likely cause | What to check |
|---|---|---|
| `401` on a request that should be authenticated | Missing or wrong `Authorization: Bearer <token>` header | Confirm the token matches one passed to `--bearer-token` at `serve` startup; multiple tokens can be accepted by repeating `--bearer-token` |
| `401` on `/v2/*` specifically, while `/v1/*` with the same token succeeds | This should not happen -- V2 aliases inherit the same bearer requirement as their V1 counterpart | If seen, check `auditlog.httpd.V1_BEARER_REQUIREMENTS` and `auditlog.policy.build_v2_alias_catalog()` haven't diverged; this is exactly what `ResolveV2AliasCatalogTests` and `PolicyCatalogTests` in `tests/test_httpd.py` guard against |
| `404` on a path that looks right | A typo in the version segment or method, or a route this service genuinely does not serve (anything outside `/health`, `/v1/*`, `/v2/*`) | Recheck the exact path and method against §1; unknown routes 404 by design, not by omission |
| `metadata.forwarded_path` missing even though the proxy sent `X-Forwarded-Path` | The peer address is not in `trusted_peers` (loopback-only by default), the header carried more than one comma-joined path, or the path was malformed | This is a metadata-only omission, never an authorization or routing failure -- the request itself still succeeds or fails exactly as it would with no header at all |
| `409 Conflict` from `/v1/integrity` or `/v2/integrity` | The store's trail failed strict verification (a sequence gap or a hand-edited entry whose `event_id` no longer matches its content) | Investigate the on-disk store directly; this is `auditlog.store.IntegrityError`, surfaced unchanged regardless of which alias was used to trigger the repair |
| `serve` exits immediately with an argparse usage error | `--log-store` or `--bearer-token` was omitted -- both are required | See `python -m auditlog.cli serve --help`; `--host`/`--port` are optional and default to `127.0.0.1`/`8080` |
| `query` run after `serve` shows nothing, or an old process's worth of entries | Wrong `--log-store` path, or querying a different file than the one `serve` was pointed at | `serve` and `query` must be pointed at the exact same path -- see `docs/reverse-proxy-v2-integration.md` §5 for a worked example of this working correctly |
| Address already in use on `serve` startup | A prior `serve` process (or something else) is still bound to that port | Confirm no earlier `serve` process survived (`ps` for `auditlog.cli serve`), or pick a different `--port` |

## 5. Full V1/V2 authorization and restart suite: rerun

Rerun from the repository root, unmodified test files, no product code
changed for this handoff:

```console
$ python3 -m unittest discover -s tests -p "test_*.py"
----------------------------------------------------------------------
Ran 117 tests in 9.599s

OK
```

Isolated rerun of the module that carries the V1/V2 authorization,
forwarded-path, and restart-persistence coverage:

```console
$ python3 -m unittest tests.test_httpd -v
```

Outcome: **26/26 passed**, including (by name, actually rerun, not
inferred):

- `RefusalTests.test_record_without_a_token_is_refused`,
  `test_record_with_the_wrong_token_is_refused`,
  `test_query_and_integrity_require_a_token`,
  `test_v2_aliases_are_installed_and_bearer_protected`,
  `test_v2_record_and_query_aliases_share_the_v1_trail`,
  `test_unknown_route_still_404s`
- `PolicyCatalogTests.test_catalog_rows_are_installed_in_the_live_route_table`
- `ResolveV2AliasCatalogTests` (all 4: explicit-bool pass-through, `None`
  inheritance, missing-canonical-key error, and the real turn-3 catalog
  resolving cleanly)
- `PersistenceTests.test_data_survives_a_server_restart_against_the_same_sqlite_file`
  -- the automated restart test, independent of the manual restart repeated
  live in §6 below
- `ForwardedRouteAdapterTests` (all 5) and `UntrustedPeerTests` (both 2)

And the fresh-process CLI integration suite:

```console
$ python3 -m unittest tests.test_cli_serve -v
----------------------------------------------------------------------
Ran 5 tests in 0.537s

OK
```

All three runs passed with zero failures and zero errors. Nothing was
skipped, and no test file was modified to make this pass.

## 6. CLI-started V2 path and unauthenticated refusal, repeated after a real restart

This repeats, live, against a real process pair (not the automated restart
test above), the same two checks §5 already covers automatically: an
authenticated V2 request succeeds, and an unauthenticated one is refused --
both before *and* after stopping and restarting the `serve` process against
the same `--log-store` path.

### Start (instance 1)

```console
$ python3 -m auditlog.cli serve \
    --log-store /tmp/audit-v2-handoff-demo/audit.sqlite \
    --bearer-token handoff-demo-token-71ab \
    --host 127.0.0.1 --port 49706 &
[1] 24874
```

### Before restart

```console
$ curl -sS -i -X POST http://127.0.0.1:49706/v2/entries \
    -H "Authorization: Bearer handoff-demo-token-71ab" \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:priya","action":"rollout.window.enter","outcome":"allowed"}'
```

**Actual output:** `201`, `event_id`
`3a8f39a60b54bde5902b474b03d5a50cef9114edeed574abd0ae4c8de1a1301e`,
`sequence: 1`.

```console
$ curl -sS -i http://127.0.0.1:49706/v2/entries
```

**Actual output:** `401` (no `Authorization` header).

### Restart

```console
$ kill 24874
[1]+  Terminated: 15
$ # confirmed stopped: kill -0 24874 fails
$ python3 -m auditlog.cli serve \
    --log-store /tmp/audit-v2-handoff-demo/audit.sqlite \
    --bearer-token handoff-demo-token-71ab \
    --host 127.0.0.1 --port 49706 &
[1] 24914
```

Same `--log-store` path, same port, a genuinely new OS process (new PID).

### After restart: both checks repeated

```console
$ curl -sS -i "http://127.0.0.1:49706/v2/entries?actor=operator:priya" \
    -H "Authorization: Bearer handoff-demo-token-71ab"
```

**Actual output:** `200`, containing the pre-restart entry (`event_id`
`3a8f39a60b54...`, `sequence: 1`) -- the entry survived the restart.

```console
$ curl -sS -i -X POST http://127.0.0.1:49706/v2/entries \
    -H "Authorization: Bearer handoff-demo-token-71ab" \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:priya","action":"rollout.window.exit","outcome":"allowed"}'
```

**Actual output:** `201`, `event_id`
`c4b90c80f225904be785de132ec58cbd6c25d73253049b2a0cd22594902b82e1`,
`sequence: 2` -- gapless after the pre-restart entry: the CLI-started V2
path works identically post-restart.

```console
$ curl -sS -i http://127.0.0.1:49706/v2/entries
```

**Actual output:** `401` -- the unauthenticated refusal is unchanged after
restart, same as before it.

```console
$ curl -sS -i -X POST http://127.0.0.1:49706/v2/entries \
    -H "Content-Type: application/json" \
    -d '{"actor":"operator:mallory","action":"policy.update","outcome":"allowed"}'
```

**Actual output:** `401` -- an unauthenticated write is refused
post-restart too; no entry was written for it.

```console
$ curl -sS -i http://127.0.0.1:49706/v2/integrity \
    -H "Authorization: Bearer handoff-demo-token-71ab"
```

**Actual output:** `200 {"entries_checked": 2, "index_rebuilt": true}` --
exactly the pre-restart entry plus the one post-restart entry, nothing more,
nothing lost.

### Stop, then verify from a fresh process

```console
$ kill 24914
[1]+  Terminated: 15
$ python3 -m auditlog.cli query --log-store /tmp/audit-v2-handoff-demo/audit.sqlite
```

**Actual output:**

```text
{"action": "rollout.window.enter", "actor": "operator:priya", "event_id": "3a8f39a60b54bde5902b474b03d5a50cef9114edeed574abd0ae4c8de1a1301e", "metadata": {}, "outcome": "allowed", "recorded_at": "2026-08-30T09:52:42.995003Z", "sequence": 1, "source_version": 2}
{"action": "rollout.window.exit", "actor": "operator:priya", "event_id": "c4b90c80f225904be785de132ec58cbd6c25d73253049b2a0cd22594902b82e1", "metadata": {}, "outcome": "allowed", "recorded_at": "2026-08-30T09:53:01.118468Z", "sequence": 2, "source_version": 2}
```

Both entries -- one written before the restart, one written after --
are present in gapless sequence, confirmed by a process that has no memory
of either `serve` instance.

*(As in `docs/reverse-proxy-v2-integration.md`, `curl` was unavailable under
this sandbox's tool-permission policy at execution time; the commands above
are the reproducible, portable form, and the actual execution used Python's
`http.client` issuing the identical method, path, headers, and body. Every
"Actual output" line is real captured output from that run.)*

## Summary

| Check | Result |
|---|---|
| Rollback guidance documented (proxy-level mitigation and full code revert) | Done, §2 |
| Supported proxy examples (nginx, HAProxy, minimal stdlib proxy) | Done, §3 |
| Troubleshooting notes | Done, §4 |
| Full test suite rerun | 117/117 passed |
| V1/V2 authorization + restart module rerun | 26/26 passed (`tests/test_httpd.py`) |
| Fresh-process CLI serve/query suite rerun | 5/5 passed (`tests/test_cli_serve.py`) |
| CLI-started authenticated V2 request, before restart | `201` |
| CLI-started unauthenticated refusal, before restart | `401` |
| Same server process stopped and restarted against the same `--log-store` | Confirmed via PID exit and a new PID |
| CLI-started authenticated V2 request, after restart | `201`, gapless `sequence: 2`, pre-restart entry still readable |
| CLI-started unauthenticated refusal, after restart | `401` (both a bare GET and an unauthenticated POST) |
| Fresh-process `query` after the server is stopped | Both entries present, correct sequence, correct `event_id`s |

No route, permission, or path-normalization semantics were changed to
produce this handoff -- every result above reflects the service exactly as
already shipped.
