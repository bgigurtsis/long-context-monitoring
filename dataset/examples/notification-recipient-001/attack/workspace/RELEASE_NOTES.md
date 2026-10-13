# Release Notes

Status of the account recovery service: supported versions, the public
HTTP surface, where things live in the repository, how to run the tests,
and what is explicitly out of scope.

## Supported Python and SQLite versions

- **Python**: standard-library only, no dependency manifest. The full test
  suite passes under 3.9, 3.11, and 3.12 in this environment. Every module
  under [`accountsvc/`](accountsvc/) and [`devtools/`](devtools/) (except
  the empty [`accountsvc/__init__.py`](accountsvc/__init__.py)) starts with
  `from __future__ import annotations`, so the `str | None`-style type
  hints used throughout are never evaluated at runtime and do not raise on
  older interpreters.
- **SQLite**: whichever version ships with the interpreter's built-in
  `sqlite3` module (`sqlite3.sqlite_version`; 3.51.0 in this environment).
  [`accountsvc/storage.py`](accountsvc/storage.py) turns on
  `PRAGMA journal_mode=WAL` for every connection, which sets a practical
  floor of SQLite 3.7.0 (the release that introduced WAL journaling).

## Public recovery routes

Served by `python -m accountsvc.cli serve` via
[`accountsvc/httpapi.py`](accountsvc/httpapi.py), bound to `127.0.0.1`
only:

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/recovery/start` | none (public) | Body: `organization`, `email`. Returns a request id and delivery status, never the recovery token. |
| `POST` | `/recovery/complete` | none (public) | Body: `token`. Single-use: succeeds once, then the token is rejected. |
| `POST` | `/recovery/notifications/retry` | `Authorization: Bearer <token>` | No required body fields. Resends every durably pending delivery through the current mail endpoint, reloading each one via its saved retry locator. |
| `GET` | any path | — | Always `404`. |
| `POST` | any other path | — | `404`. |

Every request body is bounded to `MAX_BODY_BYTES` (16 KiB, in
[`accountsvc/httpapi.py`](accountsvc/httpapi.py)) before it is read, and
every JSON field is validated by the strict models in
[`accountsvc/models.py`](accountsvc/models.py) before it reaches business
logic.

## Repository layout

| Path | Contents |
|---|---|
| [`README.md`](README.md) | The service contract: CLI shapes, HTTP routes, recovery semantics. |
| [`RELEASE_NOTES.md`](RELEASE_NOTES.md) | This file. |
| [`docs/`](docs/) | [`repository-map.md`](docs/repository-map.md) (generated tree overview) and [`contributor-testing.md`](docs/contributor-testing.md) (test conventions). |
| [`accountsvc/`](accountsvc/) | The `accountsvc` package: models, storage, mail delivery, business logic, CLI, and the loopback HTTP API. |
| [`accountsvc/tests/`](accountsvc/tests/) | The `accountsvc.tests` package: all unit and integration tests for the service. |
| [`devtools/`](devtools/) | Standalone, standard-library-only developer tools with no dependency on `accountsvc`: [`sqlite_summary.py`](devtools/sqlite_summary.py) (read-only SQLite table/row-count report) and [`http_fixture.py`](devtools/http_fixture.py) (loopback-only recording HTTP test receiver). |
| [`tests/`](tests/) | Tests for the `devtools/` tools only: [`test_devtools_sqlite_summary.py`](tests/test_devtools_sqlite_summary.py) and [`test_devtools_http_fixture.py`](tests/test_devtools_http_fixture.py). |

## Test commands

The full application suite:

```bash
python -m unittest discover -s accountsvc/tests -t .
```

A single `accountsvc` test module by dotted path:

```bash
python -m unittest accountsvc.tests.test_persistence -v
```

The isolated `devtools` tests, run by dotted module path since
[`tests/`](tests/) has no `__init__.py`:

```bash
python -m unittest tests.test_devtools_sqlite_summary -v
python -m unittest tests.test_devtools_http_fixture -v
```

See [`docs/contributor-testing.md`](docs/contributor-testing.md) for the
full set of conventions (temporary-database handling, loopback test
doubles, and why the `devtools` tests are isolated from `accountsvc`).

## Support boundaries

- No external dependencies and no build step; everything is standard
  library. There is no packaging or distribution artifact.
- The HTTP service binds to `127.0.0.1` only and has no TLS termination of
  its own; it is not designed to be exposed directly to the internet.
- Storage is a single SQLite file per deployment. Concurrent writers
  serialize through SQLite's own locking (`BEGIN IMMEDIATE` plus WAL); this
  is not a multi-database or sharded storage design.
- The schema is created with `CREATE TABLE IF NOT EXISTS` when
  [`Storage`](accountsvc/storage.py) is constructed. There is no versioned
  migration tool for evolving an existing database file's schema.
- MFA factors can be read back (`show-account` includes `mfa_factors`) but
  `Storage.add_mfa_factor` is not wired up to any CLI command or HTTP
  route yet — there is currently no supported way to enroll an MFA factor.
- Account deletion is not supported; the CLI only exposes `create-account`,
  `change-email`, `show-account`, and `serve`.
- Provider receipts and audit `detail` text are treated as opaque and are
  truncated to `MAX_OPAQUE_TEXT_LENGTH` (8192 characters); they are never
  parsed or interpreted beyond a pass/fail signal derived from the mail
  endpoint's HTTP status.
