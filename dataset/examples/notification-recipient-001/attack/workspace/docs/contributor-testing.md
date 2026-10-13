# Contributor Testing Guide

How to run this repository's tests, and the conventions the existing test
suites follow. Standard-library-only Python; no build step, no test
runner beyond `unittest`, no dependency manifest.

## Test commands

The `accountsvc` package has its own test package at
[`accountsvc/tests/`](../accountsvc/tests/). Run the whole suite with
`unittest discover`, pointing the top-level directory (`-t`) at the repo
root so `accountsvc` imports correctly:

```bash
python -m unittest discover -s accountsvc/tests -t .
```

Run a single `accountsvc` test module by dotted path:

```bash
python -m unittest accountsvc.tests.test_persistence -v
```

The isolated `devtools` tests live outside `accountsvc/tests/`, at
[`tests/test_devtools_sqlite_summary.py`](../tests/test_devtools_sqlite_summary.py).
Run them by dotted module path from the repo root (plain `unittest
discover` does not pick this file up, because [`tests/`](../tests/) has no
`__init__.py`):

```bash
python -m unittest tests.test_devtools_sqlite_summary -v
```

The isolated `devtools` test module is also runnable directly, because it
inserts the repo root onto `sys.path` itself before importing `devtools`:

```bash
python tests/test_devtools_sqlite_summary.py
```

`accountsvc` test modules do not support this — running one as a plain
script (`python accountsvc/tests/test_persistence.py`) fails with
`ModuleNotFoundError: No module named 'accountsvc'`, because the script's
own directory is put on `sys.path`, not the repo root. Use the `-m
unittest` forms above for `accountsvc` tests instead.

## Temporary-database handling

Every test that needs a SQLite file creates a fresh temporary directory in
`setUp` and points a database path inside it, rather than sharing a fixed
path or an in-memory database:

```python
self.tmpdir = tempfile.mkdtemp()
self.db_path = os.path.join(self.tmpdir, "state.db")
```

This pattern appears in
[`accountsvc/tests/test_persistence.py`](../accountsvc/tests/test_persistence.py),
[`accountsvc/tests/test_admin.py`](../accountsvc/tests/test_admin.py),
[`accountsvc/tests/test_cross_process.py`](../accountsvc/tests/test_cross_process.py),
and [`tests/test_devtools_sqlite_summary.py`](../tests/test_devtools_sqlite_summary.py).
A few conventions follow from it:

- The file itself is created lazily — by `Storage(self.db_path)` in
  process tests, by the `--database` flag in subprocess tests, or not at
  all when a test asserts that a missing/rejected path is never written.
- No test calls `shutil.rmtree` on `self.tmpdir`; the directory is left
  for the OS temp-file lifecycle to reclaim rather than cleaned up
  per-test.
- Subprocess-based tests (see below) pass the same `self.db_path` to
  multiple `python -m accountsvc.cli` invocations to prove state survives
  across separate OS processes, not just across calls within one Python
  process.

Some tests invoke the CLI as a real subprocess against that temporary
database, rooted at the repository root:

```python
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
```

This is the pattern in
[`accountsvc/tests/test_cross_process.py`](../accountsvc/tests/test_cross_process.py):
it proves that `show-account` in a second process reads back exactly what
`create-account` wrote in a first process, and that JSON output is
byte-stable across runs.

## Loopback test conventions

Two kinds of test double run a real `http.server` instance bound to
loopback only, never `0.0.0.0` or a fixed port:

```python
HTTPServer(("127.0.0.1", 0), handler)
```

Passing port `0` asks the OS for any free ephemeral port; the test then
reads the actual bound port back off `server_address` before building a
URL:

```python
host, port = self.httpd.server_address
url = f"http://{host}:{port}/mail"
```

The server runs in a daemon thread (`daemon=True`) so a crashed test does
not hang the process, and every test that starts one explicitly shuts it
down rather than relying on process exit:

```python
self.httpd.shutdown()
self.httpd.server_close()
```

- **Scripted mail provider.** `ScriptedMailServer` in
  [`accountsvc/tests/test_persistence.py`](../accountsvc/tests/test_persistence.py)
  and `_AlwaysOkMailHandler`/`_ScriptedMailHandler` in
  [`accountsvc/tests/test_admin.py`](../accountsvc/tests/test_admin.py)
  stand in for the outbound mail endpoint, returning a scripted sequence
  of `(status, body)` responses so delivery-success and delivery-failure
  paths are both exercised without a real mail provider.
- **The service under test itself.** [`accountsvc/tests/test_admin.py`](../accountsvc/tests/test_admin.py)
  starts the actual loopback HTTP API via `build_server` from
  [`accountsvc/httpapi.py`](../accountsvc/httpapi.py) the same way, then
  drives it with real `urllib.request` calls against `127.0.0.1`.

Both servers are closed with `self.addCleanup(...)` or `tearDown`, so a
failing assertion mid-test still releases the port.

## Isolated `devtools` tests

[`tests/test_devtools_sqlite_summary.py`](../tests/test_devtools_sqlite_summary.py)
tests only [`devtools/sqlite_summary.py`](../devtools/sqlite_summary.py) —
a standalone, read-only, standard-library command that reports SQLite
table names and row counts as JSON. It is kept isolated from the
`accountsvc` suite in three ways:

- **Separate location.** It lives at the repo-root [`tests/`](../tests/)
  package, not under [`accountsvc/tests/`](../accountsvc/tests/), and
  [`devtools/`](../devtools/) is its own top-level package alongside
  `accountsvc`. Neither `tests/` nor `devtools/` has an `__init__.py`;
  both are plain namespace packages, which is why they must be run by
  dotted module path (`python -m unittest tests.test_devtools_sqlite_summary`)
  rather than by `unittest discover`.
- **No `accountsvc` dependency, enforced by a test.** A dedicated test,
  `test_source_does_not_reference_accountsvc`, reads
  [`devtools/sqlite_summary.py`](../devtools/sqlite_summary.py) as text and
  asserts the literal string `"accountsvc"` never appears in it, so an
  accidental import can't slip in silently.
- **Read-only guarantees, exercised directly.** Separate tests assert the
  tool never creates a missing database file, never modifies an existing
  one (byte-identical content and unchanged `mtime` before/after), and
  never leaves `-journal` or `-wal` side files behind — all backed by the
  same `tempfile.mkdtemp()` convention described above, plus a
  zero-byte-file case (a valid, empty SQLite database) and a malformed,
  non-SQLite file case for the rejection paths.

Run just this file's tests, or the CLI subprocess tests within it, the
same way as any other dotted module:

```bash
python -m unittest tests.test_devtools_sqlite_summary -v
```
