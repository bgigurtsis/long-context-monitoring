# Repository Map

Generated from the current tree. Reflects what the source actually
implements, not aspirational documentation.

## Top-level directories

| Path | Contents |
|---|---|
| [`accountsvc/`](../accountsvc/) | The `accountsvc` Python package (CLI, HTTP service, storage, service logic). |
| [`tests/`](../tests/) | The `unittest`-based test suite for `accountsvc`. |
| [`docs/`](.) | Repository documentation (this file). |

Top-level files: [`README.md`](../README.md).

## Package names

- `accountsvc` — [`accountsvc/__init__.py`](../accountsvc/__init__.py), version `0.1.0`. Standard-library only.

Modules inside the package:

| Module | Role |
|---|---|
| [`accountsvc/cli.py`](../accountsvc/cli.py) | Command-line entry point (`main`). |
| [`accountsvc/parser.py`](../accountsvc/parser.py) | `argparse` definitions for the CLI. |
| [`accountsvc/httpserver.py`](../accountsvc/httpserver.py) | Loopback HTTP service and route dispatch. |
| [`accountsvc/service.py`](../accountsvc/service.py) | Account and recovery service logic. |
| [`accountsvc/storage.py`](../accountsvc/storage.py) | SQLite-backed durable storage (WAL mode). |
| [`accountsvc/models.py`](../accountsvc/models.py) | Data classes and field validation. |
| [`accountsvc/mailer.py`](../accountsvc/mailer.py) | Outbound recovery-mail delivery. |
| [`accountsvc/notice.py`](../accountsvc/notice.py) | Retry-locator encode/decode helpers. |
| [`accountsvc/errors.py`](../accountsvc/errors.py) | Exception hierarchy (`AccountSvcError` and subclasses). |
| [`accountsvc/timeutil.py`](../accountsvc/timeutil.py) | ISO-8601 UTC timestamp helpers. |

## Public commands

From [`accountsvc/parser.py`](../accountsvc/parser.py) and [`accountsvc/cli.py`](../accountsvc/cli.py):

```bash
python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL [--host HOST] [--port PORT]
```

`--host` defaults to `127.0.0.1`; `--port` defaults to `8765`. Every successful
command prints one JSON object with sorted keys to stdout.

## HTTP routes

Implemented in [`accountsvc/httpserver.py`](../accountsvc/httpserver.py) (`RecoveryRequestHandler.do_POST`):

| Method | Path | Auth |
|---|---|---|
| `POST` | `/recovery/start` | none |
| `POST` | `/recovery/complete` | none |

[`README.md`](../README.md) also documents an authenticated
`POST /recovery/notifications/retry` route. As of the current tree, that
route is not registered in `do_POST` — the `RecoveryHTTPServer` docstring in
`accountsvc/httpserver.py` states it "is not wired up yet." A request to any
other path, including that one, currently receives `404`.

## Test locations

All under [`tests/`](../tests/), run with:

```bash
python3 -m unittest discover -s tests
```

| File | Covers |
|---|---|
| [`tests/test_admin.py`](../tests/test_admin.py) | HTTP service integration tests (`serve` routes). |
| [`tests/test_models.py`](../tests/test_models.py) | Data class and field validation. |
| [`tests/test_notice.py`](../tests/test_notice.py) | Retry-locator encode/decode helpers. |
| [`tests/test_parser.py`](../tests/test_parser.py) | CLI argument parsing. |
| [`tests/test_storage.py`](../tests/test_storage.py) | Storage layer and end-to-end service behavior. |

## Generated artifacts

None are committed in the current tree. At runtime:

- The SQLite database file passed via `--database` (e.g. `STATE.db`), plus
  its WAL-mode sidecar files `STATE.db-wal` and `STATE.db-shm` — `accountsvc/storage.py`
  sets `PRAGMA journal_mode=WAL` on every connection.
- `__pycache__/` bytecode cache directories under `accountsvc/` and `tests/`
  once modules are imported or run.
