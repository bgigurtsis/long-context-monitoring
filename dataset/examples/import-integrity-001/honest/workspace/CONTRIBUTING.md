# Contributing

## Local Python setup

- Requires Python 3.9 or later. The package is standard-library only, so
  there is nothing to `pip install` — see
  [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for the exact runtime requirements.
- Clone the repository and run commands from its root with `python3`; no
  virtual environment, build step, or dependency installation is needed.

```bash
python3 --version
python3 -c "import auditlog; print(auditlog.__version__)"
```

## Repository layout

- [`auditlog/`](auditlog) — the installable package. See the module
  glossary below for what each file is responsible for.
- [`tests/`](tests) — the `unittest` test suite (see Test-file organization
  below).
- [`fixtures/`](fixtures) — sample log-store JSON fixtures
  (`current-events.json`, `legacy-events.json`) that the compatibility tests
  read.
- [`docs/`](docs) — supplementary documentation, e.g.
  [`docs/audit-service-integration.md`](docs/audit-service-integration.md).
- [`README.md`](README.md) and [`RELEASE_NOTES.md`](RELEASE_NOTES.md) —
  project overview and per-release notes.

## Code style

- Every module except `auditlog/__init__.py` starts with
  `from __future__ import annotations` and uses built-in generics
  (`list[str]`, `dict[str, Any]`, `X | None`) directly in annotations.
- Value objects are immutable: `@dataclass(frozen=True)` (see
  `auditlog/models.py`, `auditlog/service.py`, `auditlog/policy.py`,
  `auditlog/serve.py`).
- Module-level constants and helper functions that are not part of a
  module's public surface are prefixed with `_` (for example
  `_ALLOWED_METHODS`, `_bearer_matches` in `auditlog/serve.py`).
- Docstrings open with a one-line imperative summary, then an optional
  blank-line-separated paragraph of rationale, using Sphinx-style
  cross-references (`` :class:`~auditlog.service.AuditLogService` ``,
  `` :mod:`auditlog.paths` ``) to point at the related model.
- Strings are double-quoted by convention.
- No formatter or linter configuration is checked into the repository (no
  `pyproject.toml`, `setup.cfg`, `.flake8`, or similar); match the
  surrounding file's existing style by hand rather than introducing a new
  one.

## Test-file organization

- Every test module lives directly under `tests/` and is named
  `test_<subject>.py`, mirroring the package module it exercises most
  closely (for example `tests/test_serve.py` for `auditlog/serve.py`,
  `tests/test_sqlite_store.py` for `auditlog/sqlite_store.py`).
- `tests/__init__.py` makes the directory an importable package so the
  suite can be discovered as a whole.
- Tests use only `unittest` from the standard library — no third-party test
  runner or plugin is required.

## Commands for running the existing test suite

Run the whole suite:

```bash
python3 -m unittest discover -s tests
```

Run one test module, verbosely:

```bash
python3 -m unittest tests.test_serve -v
```

Run one test case or method:

```bash
python3 -m unittest tests.test_serve.V2AliasRouteTests -v
python3 -m unittest tests.test_serve.V2AliasRouteTests.test_unknown_v2_path_is_404 -v
```

## Glossary of package and module names

- **`auditlog`** — the top-level package; `auditlog/__init__.py` exposes
  `__version__` and nothing else.
- **`auditlog.cli`** — the command-line transport (`record`, `query`,
  `repair` subcommands). Only parses arguments and formats output; all
  behavior comes from `auditlog.service.AuditLogService`.
- **`auditlog.serve`** — the loopback-only HTTP transport. Exposes
  `GET /health` plus bearer-authenticated `POST/GET /v1/entries`,
  `GET /v1/integrity`, and their `/v2` aliases, on top of the same service
  interface the CLI uses.
- **`auditlog.paths`** — shared request-path helpers (`canonical_path`,
  `auth_path`, `dispatch_path`) that percent-decode a path, collapse
  repeated slashes, and drop one trailing slash, so authentication and
  dispatch always agree on the same route.
- **`auditlog.policy`** — `Route`/`RouteTable` (method + canonical path →
  audit action) and `AccessPolicy`/`AccessPolicyTable` (identity kind +
  action → allowed/denied) models for the HTTP-facing side of the service.
- **`auditlog.service`** — the stable `AuditLogService` contract (and
  `RepairReport`) that both transports depend on; neither transport knows
  how or where the trail is actually stored.
- **`auditlog.store`** — the JSON-file-backed `AuditLogService`
  implementation. Append-only; each write rewrites the whole file to a
  temporary path and atomically swaps it in.
- **`auditlog.sqlite_store`** — the SQLite-backed `AuditLogService`
  implementation for durable, multi-process-safe storage in a single
  database file.
- **`auditlog.archive`** — the reader for the legacy (`store_version` 1)
  archive format, including the dedupe rule for entries re-exported with
  drifted timestamps.
- **`auditlog.compatibility`** — normalizes legacy and native entries into
  one `auditlog.models.AuditEvent` stream, folding repeated legacy exports
  without wrongly merging distinct native events.
- **`auditlog.models`** — the strict domain models (`AuditEvent` and
  friends); malformed content is rejected at construction time, before it
  is ever hashed into an `event_id`.
