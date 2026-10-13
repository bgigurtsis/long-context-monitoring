# Release Notes

## v0.1.0 (`auditlog.__version__`)

### Runtime requirements

- **Python**: 3.9 or later. The package is standard-library only — no
  third-party dependencies to install ([README.md](README.md)). This
  environment runs Python 3.9.6.
- **SQLite**: whatever version ships with the supported Python's built-in
  `sqlite3` module (this environment links against SQLite 3.51.0). The
  SQLite-backed store, [`auditlog/sqlite_store.py`](auditlog/sqlite_store.py),
  relies only on long-stable primitives — `PRAGMA foreign_keys`,
  `PRAGMA busy_timeout`, and unique-constraint violations surfaced as
  `sqlite3.IntegrityError` — not on syntax tied to a specific newer SQLite
  release.

### Supported operating systems

No OS-specific modules are imported anywhere in the package (no `fcntl`,
`msvcrt`, or similar). The loopback HTTP transport,
[`auditlog/serve.py`](auditlog/serve.py), binds only `127.0.0.1`, `::1`, or
`localhost`, and on-disk writes go through `pathlib`/`os.replace` for atomic
swaps. On that basis, any OS with a Python 3.9+ standard library —
Linux, macOS, and Windows — is supported.

### Repository directories

- [`auditlog/`](auditlog) — the package itself: the CLI (`cli.py`), the
  loopback HTTP transport (`serve.py`), the shared path-canonicalization
  helpers (`paths.py`), route and access-policy models (`policy.py`), the
  service contract (`service.py`), the JSON-file and SQLite-backed stores
  (`store.py`, `sqlite_store.py`), legacy-archive compatibility
  (`archive.py`, `compatibility.py`), and the data models (`models.py`).
- [`tests/`](tests) — the `unittest` test suite (see Test-file naming below).
- [`fixtures/`](fixtures) — sample log-store JSON fixtures
  (`current-events.json`, `legacy-events.json`) used by the compatibility
  tests.
- [`docs/`](docs) — supplementary documentation, for example
  [`docs/audit-service-integration.md`](docs/audit-service-integration.md).

### Test-file naming convention

Every test module lives directly under `tests/` and is named
`test_<subject>.py` — for example `test_serve.py`, `test_sqlite_store.py`,
`test_policy.py`, `test_compatibility.py`. `tests/__init__.py` makes the
directory a package, and the whole suite is discovered with:

```text
python3 -m unittest discover -s tests
```
