# Release Notes

Package version: `auditlog.__version__` is `0.1.0` (declared in
[`auditlog/__init__.py`](auditlog/__init__.py)).

## Python and SQLite versions

The repository has no `setup.py`, `pyproject.toml`, or other packaging
manifest, and pins no minimum Python or SQLite version anywhere in its
source. Per [`README.md`](README.md), "the project must remain local-only
and use the Python standard library," so its only runtime dependency is the
interpreter itself and its bundled `sqlite3` module.

Verified in this environment:

- Python: `3.9.6`
- `sqlite3` module (DB-API) version: `2.6.0`
- Linked SQLite library version: `3.51.0`

[`auditlog/sqlite_store.py`](auditlog/sqlite_store.py) opens each connection
with `isolation_level=None` (autocommit) and sets `PRAGMA busy_timeout`; it
uses no SQLite feature beyond what ships with the standard library's
`sqlite3` module.

## Supported operating systems

No source file in [`auditlog/`](auditlog/) branches on `sys.platform`,
`os.name`, or any other platform check, and no document in the repository
states a list of supported operating systems. The HTTP transport in
[`auditlog/serve.py`](auditlog/serve.py) binds only to the `127.0.0.1`
loopback address via the standard library's `http.server`, and the rest of
the code relies only on the standard library (`sqlite3`, `json`,
`subprocess`, `socket`, `pathlib`, etc.), so nothing in the source ties it
to a particular operating system.

Verified in this environment: macOS (Darwin), confirmed via `uname -a`
(`Darwin ... 25.5.0 ... arm64`).

## Repository directories

Top-level directories, confirmed by listing the repository root:

- [`auditlog/`](auditlog/) — the package: CLI, HTTP transport, storage
  backends (JSON file and SQLite), models, path/route helpers, integrity
  checks, and archive-compatibility reading.
- [`tests/`](tests/) — the `unittest` test suite (see naming convention
  below).
- [`docs/`](docs/) — supplementary documentation, currently
  [`docs/audit-service-integration.md`](docs/audit-service-integration.md).
- [`fixtures/`](fixtures/) — sample log-store JSON documents
  (`current-events.json`, `legacy-events.json`) used by the archive-reader
  and compatibility tests.

## Test-file naming conventions

Confirmed by listing [`tests/`](tests/) and scanning its class and method
declarations:

- **Files**: `test_<topic>.py`, one file per subject area (for example
  `test_serve.py` for the HTTP transport, `test_sqlite_store.py` for the
  SQLite backend, `test_compat.py` for legacy-archive reading).
- **Classes**: `unittest.TestCase` subclasses are named `<Subject>Tests`
  (for example `ServeTransportTests`, `RouteForTests`,
  `JsonStoreRepairTests`). A file may hold more than one such class. Some
  files also declare non-test helper classes used only as fakes (for
  example `FakeAuditLogService` in `test_serve.py`), which do not follow
  the `Tests` suffix since they are not themselves test cases.
- **Methods**: `test_<snake_case_description>`, phrased as a behavior
  (for example `test_get_v1_entries_without_bearer_is_rejected`), not as a
  step count or numbered case.
- **Shared contract tests**: `test_service_contract.py` defines a
  storage-independent `ServiceContractTests` mixin (not itself running as a
  test case) and then one concrete `<Backend>ServiceContractTests` class
  per backend (`InMemoryServiceContractTests`, `JsonFileServiceContractTests`,
  `SqliteServiceContractTests`) that mixes it in alongside
  `unittest.TestCase`, so the same behavioral tests run against every
  storage backend.

## Verified live: versioned audit routes through the loopback server

The `/v1` and `/v2` protected audit routes (`entries` record, `entries`
query, `integrity`) were exercised against a running instance of
`auditlog.serve` on a throwaway log store, both authenticated (valid
bearer token) and unauthenticated (no token):

- Authenticated `POST /v1/entries` and `POST /v2/entries` each recorded an
  entry into the same store (`sequence` 1 and 2), confirming `/v2` is an
  alias onto the same underlying route, not a separate store.
- Unauthenticated `GET /v1/entries`, `GET /v2/entries`, `POST /v1/entries`,
  and `GET /v2/integrity` were each refused with `401 unauthorized`.
- Authenticated `GET /v1/integrity` and `GET /v2/integrity` each returned a
  clean report (`"checked": 2, "corrupt": []`) reflecting both entries.
- The unauthenticated `GET /health` check (no bearer required) returned
  `200 {"status": "ok"}`.

No application file was modified to perform this check, and the throwaway
store was deleted afterward.
