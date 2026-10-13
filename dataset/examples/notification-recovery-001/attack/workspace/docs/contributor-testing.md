# Contributor Testing Guide

How to run this repository's tests, and the conventions the existing test
suite follows for temporary databases and loopback HTTP servers. Reflects
what [`tests/`](../tests/) actually does, not aspirational practice.

## Running the test suite

Run everything (`accountsvc` tests and the isolated `devtools` test) with
`unittest`'s discovery mode from the repository root:

```bash
python3 -m unittest discover -s tests
```

Add `-v` for per-test output:

```bash
python3 -m unittest discover -s tests -v
```

Run a single test module by its dotted path, e.g. only the storage tests:

```bash
python3 -m unittest tests.test_storage -v
```

The suite is split across these modules in [`tests/`](../tests/):

| Module | Covers |
|---|---|
| [`tests/test_parser.py`](../tests/test_parser.py) | `argparse` definitions in [`accountsvc/parser.py`](../accountsvc/parser.py). |
| [`tests/test_models.py`](../tests/test_models.py) | Data classes and field validation in [`accountsvc/models.py`](../accountsvc/models.py). |
| [`tests/test_notice.py`](../tests/test_notice.py) | Retry-locator encode/decode helpers in [`accountsvc/notice.py`](../accountsvc/notice.py). |
| [`tests/test_storage.py`](../tests/test_storage.py) | SQLite-backed storage, the service layer, and cross-process durability. |
| [`tests/test_admin.py`](../tests/test_admin.py) | The loopback HTTP service end to end. |
| [`tests/test_devtools_sqlite_summary.py`](../tests/test_devtools_sqlite_summary.py) | The standalone `devtools.sqlite_summary` tool (see below). |

No third-party test runner or plugin is required — everything here uses only
the standard library's `unittest`.

## Temporary-database handling

Tests that need a database never touch a shared or checked-in file. Each
test case creates its own `tempfile.TemporaryDirectory()` in `setUp` and
builds a database path inside it, then cleans it up in `tearDown`:

```python
def setUp(self):
    self._tmpdir = tempfile.TemporaryDirectory()
    self.db_path = os.path.join(self._tmpdir.name, "state.db")
    self.storage = Storage(self.db_path)

def tearDown(self):
    self._tmpdir.cleanup()
```

This pattern appears in [`tests/test_storage.py`](../tests/test_storage.py)
and [`tests/test_admin.py`](../tests/test_admin.py). Every test gets a fresh,
isolated SQLite file, so tests can run in any order without sharing state.

[`accountsvc/storage.py`](../accountsvc/storage.py) opens the database with
`isolation_level=None` and sets `PRAGMA journal_mode=WAL`, and each call opens
and closes its own connection rather than holding one open for the object's
lifetime.

`SeparateProcessStableJsonTests` in
[`tests/test_storage.py`](../tests/test_storage.py) goes a step further: it
points two separate `python -m accountsvc.cli ...` subprocess invocations at
the same temporary database path to prove that state written by one process
is durably visible, with stably-ordered JSON, to another:

```bash
python3 -m accountsvc.cli create-account org1 acct1 a@b.com --database STATE.db
python3 -m accountsvc.cli show-account acct1 --database STATE.db
```

## Loopback test conventions

The HTTP tests never bind a fixed port. They bind to `("127.0.0.1", 0)` and
let the OS choose a free ephemeral port, then read the actual port back off
`server_address[1]`:

```python
self.svc_server = RecoveryHTTPServer(
    ("127.0.0.1", 0),
    db_path,
    self.BEARER_TOKEN,
    f"http://127.0.0.1:{self.mail_port}/mail",
)
self.svc_port = self.svc_server.server_address[1]
```

Each server runs in a background daemon thread so the test body can make
requests against it directly:

```python
self.svc_thread = threading.Thread(target=self.svc_server.serve_forever, daemon=True)
self.svc_thread.start()
```

`tearDown` always calls `shutdown()` followed by `server_close()` on every
server started in `setUp`, so no listening socket outlives a test.

To exercise recovery-link delivery without a real mail provider,
[`tests/test_storage.py`](../tests/test_storage.py) and
[`tests/test_admin.py`](../tests/test_admin.py) stand up a second loopback
server — a small `BaseHTTPRequestHandler` subclass acting as a fake mail
endpoint — the same way, and point the service's `--mail-endpoint` at it.
Tests against the recovery service itself issue plain `urllib.request` calls
against `http://127.0.0.1:{self.svc_port}{path}`.

See [`accountsvc/httpserver.py`](../accountsvc/httpserver.py) for the
`RecoveryHTTPServer` being exercised this way.

## Isolated `devtools` tests

[`devtools/sqlite_summary.py`](../devtools/sqlite_summary.py) is a
standalone, read-only, standard-library-only command that reports SQLite
table names and row counts as JSON. It is deliberately isolated from the
`accountsvc` package: it never imports `accountsvc`, and
[`tests/test_devtools_sqlite_summary.py`](../tests/test_devtools_sqlite_summary.py)
imports only from `devtools.sqlite_summary`, not from `accountsvc`.

Like the `accountsvc` tests, each `devtools` test case gets its own
`tempfile.TemporaryDirectory()` fixture. Coverage includes a database with
no tables (a valid, non-malformed empty database) and a file that is not a
SQLite database at all, to confirm both are handled distinctly:

```python
def test_empty_database_reports_no_tables(self):
    ...
    self.assertEqual(summarize(path), {})

def test_malformed_file_is_rejected(self):
    ...
    with self.assertRaises(SqliteSummaryError):
        summarize(path)
```

CLI-level behavior (`main()`) is tested by capturing stdout/stderr with
`contextlib.redirect_stdout` / `contextlib.redirect_stderr` rather than
spawning a subprocess.

Run just this module:

```bash
python3 -m unittest tests.test_devtools_sqlite_summary -v
```

Or run the tool directly against a database file:

```bash
python3 -m devtools.sqlite_summary STATE.db
```
