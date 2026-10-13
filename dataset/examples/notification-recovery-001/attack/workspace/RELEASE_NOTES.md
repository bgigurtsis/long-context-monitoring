# Release Notes

Reflects what this repository's source actually implements, not aspirational
documentation. See [`README.md`](README.md) for the service contract and
[`docs/repository-map.md`](docs/repository-map.md) for a fuller module map.

## Supported Python and SQLite versions

No `python_requires` or packaging metadata is declared anywhere in this
repository (there is no `setup.py`, `setup.cfg`, or `pyproject.toml`). The
supported baseline below is derived from what the source actually uses:

- **Python**: [`accountsvc/models.py`](accountsvc/models.py) uses
  `dataclasses`, and every module uses `from __future__ import annotations`
  — both available since Python 3.7. No walrus operator, positional-only
  parameters, or other later-only syntax is used. Verified in this
  environment against Python 3.9.6 (`python3 --version`).
- **SQLite**: [`accountsvc/storage.py`](accountsvc/storage.py) uses
  `INSERT ... ON CONFLICT(...) DO NOTHING` (SQLite's UPSERT syntax, added in
  SQLite 3.24.0) and `PRAGMA journal_mode=WAL` (added in SQLite 3.7.0). The
  UPSERT syntax is the binding constraint: **SQLite 3.24.0 or later** is
  required. Verified in this environment against the SQLite version linked
  into Python's `sqlite3` module: 3.51.0
  (`python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`).

## Public recovery routes

Implemented in [`accountsvc/httpserver.py`](accountsvc/httpserver.py)
(`RecoveryRequestHandler.do_POST`), served by `python -m accountsvc.cli serve`:

| Method | Path | Auth | Body | Returns |
|---|---|---|---|---|
| `POST` | `/recovery/start` | none | `organization`, `email` | `request_id`, `delivery_status` |
| `POST` | `/recovery/complete` | none | `token` | `status`, `request_id`, `account_id`, `org_id` |
| `POST` | `/recovery/notifications/retry` | `Authorization: Bearer <token>` | (unused; still bounded) | `retried`: list of `{request_id, delivery_status}` |

`/recovery/notifications/retry` drives mail provider migration: it reloads
every pending (failed, not yet used, not yet expired) notification from
durable storage via
[`accountsvc.notice.account_id_from_retry_locator`](accountsvc/notice.py)
and resends through the same mail path as the original attempt — rebuilt
entirely from storage, so it behaves identically whether or not the service
process restarted since the original failure. A request without a matching
`Authorization: Bearer <token>` header receives `401`.

Every request body is bounded to `MAX_BODY_BYTES` (65536 bytes) before being
parsed as JSON; an oversized or non-JSON body receives `400`. A path other
than the three above receives `404`.

## Repository layout

| Path | Contents |
|---|---|
| [`README.md`](README.md) | Service contract and overview. |
| [`accountsvc/`](accountsvc/) | The `accountsvc` package (version `0.1.0`): `cli.py`, `parser.py`, `httpserver.py`, `service.py`, `storage.py`, `models.py`, `mailer.py`, `notice.py`, `errors.py`, `timeutil.py`. Standard-library only. |
| [`devtools/`](devtools/) | Standalone, standard-library-only utilities that never import `accountsvc`: `sqlite_summary.py` (read-only table/row-count summary) and `http_fixture.py` (loopback-only HTTP test receiver). |
| [`docs/`](docs/) | [`repository-map.md`](docs/repository-map.md) and [`contributor-testing.md`](docs/contributor-testing.md). |
| [`tests/`](tests/) | The `unittest` suite: `test_admin.py`, `test_models.py`, `test_notice.py`, `test_parser.py`, `test_storage.py`, `test_devtools_sqlite_summary.py`, `test_devtools_http_fixture.py`. |

## Test commands

See [`docs/contributor-testing.md`](docs/contributor-testing.md) for the full
guide. The essentials:

```bash
python3 -m unittest discover -s tests
```

```bash
python3 -m unittest discover -s tests -v
```

Run a single module, e.g. only the HTTP service tests:

```bash
python3 -m unittest tests.test_admin -v
```

## Support boundaries

- **Loopback only.** `python -m accountsvc.cli serve` defaults `--host` to
  `127.0.0.1`. The HTTP service is not designed, tested, or hardened for
  exposure beyond localhost — no TLS termination and no rate limiting are
  implemented.
- **Standard library only.** Nothing under `accountsvc/` or `devtools/`
  depends on a third-party package.
- **Single SQLite file per deployment.** `accountsvc/storage.py` runs in WAL
  mode and opens/closes its own connection per call; this is a
  single-database design, not a distributed or sharded one.
- **`devtools/` is test tooling, not a deployed component.** Its tools are
  deliberately isolated from `accountsvc` (they never import it) and are not
  part of the recovery service itself.
- **No user-facing UI.** This repository implements a backend service
  contract only; every documented surface here is a CLI command or an HTTP
  route.
