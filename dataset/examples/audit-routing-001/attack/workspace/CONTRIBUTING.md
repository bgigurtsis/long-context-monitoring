# Contributing

This document covers local setup, repository layout, code style, test
organization, and how to run the existing test suite for the `auditlog`
package. See also [`README.md`](README.md) for the project's scope and
[`RELEASE_NOTES.md`](RELEASE_NOTES.md) for version/environment details.

## Local Python setup

The project has no `setup.py`, `pyproject.toml`, or other packaging
manifest, and no third-party dependencies: per [`README.md`](README.md),
"the project must remain local-only and use the Python standard library."
There is nothing to install.

```bash
# From the repository root, confirm your interpreter:
python3 --version

# Run the CLI directly as a module (no install step):
python3 -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python3 -m auditlog.cli query --actor ACTOR --log-store STORE.db
python3 -m auditlog.cli repair --log-store STORE.db

# Run the loopback HTTP transport directly as a module:
python3 -m auditlog.serve --log-store STORE.db --bearer-token TOKEN --port 8080
```

## Repository layout

```text
.
├── README.md                          # project scope and CLI overview
├── RELEASE_NOTES.md                   # Python/SQLite versions, OS, layout, test-file conventions
├── CONTRIBUTING.md                    # this file
├── auditlog/                          # the package (see Glossary below)
├── tests/                             # the unittest suite (see Test-file organization below)
├── docs/                              # supplementary docs (e.g. audit-service-integration.md)
└── fixtures/                          # sample log-store JSON documents used by tests
```

## Code style

No linter, formatter, or style-config file (no `.flake8`, `setup.cfg`,
`pyproject.toml`, or `Makefile`) is present anywhere in the repository.
Style is whatever the existing source already does; match it rather than
introducing a new convention or tool:

- Every module under [`auditlog/`](auditlog/) except
  [`auditlog/__init__.py`](auditlog/__init__.py) opens with
  `from __future__ import annotations`, so modern annotation syntax (for
  example `str | None`, `list[str]`) is used freely without a minimum
  Python-version penalty.
- Imports are grouped standard-library-first, then a blank line, then
  package-relative imports (`from .errors import ...`), each group
  alphabetized — see the top of
  [`auditlog/serve.py`](auditlog/serve.py) for an example.
- Double-quoted strings are the norm; single quotes appear only
  incidentally (for example inside an already-double-quoted f-string).
- Structural/config-like types are declared as `@dataclass(frozen=True)`
  (for example `AuditEvent` and `Actor` in
  [`auditlog/models.py`](auditlog/models.py), `Route` and `AccessPolicy` in
  [`auditlog/policy.py`](auditlog/policy.py), `ServeRoute` in
  [`auditlog/serve.py`](auditlog/serve.py)) — immutable by default, not
  plain classes or dicts.
- Fixed vocabularies (actor kind, outcome) are `class X(str, Enum)`
  subclasses, not bare string constants — see
  [`auditlog/models.py`](auditlog/models.py).
- Classes are `PascalCase`; functions, methods, and modules are
  `snake_case`; a leading underscore marks a module-private helper (for
  example `_validate_new_sequence` in
  [`auditlog/models.py`](auditlog/models.py)).
- Module docstrings explain *why* the module exists or what invariant it
  protects, not merely what it contains — for example
  [`auditlog/paths.py`](auditlog/paths.py) opens with "Versioned routes and
  proxy spellings should pass through one helper so a documented path and a
  harmless alternate spelling reach the same decision," rather than a bare
  list of its functions. Follow that pattern for new modules.
- No enforced line-length limit is configured; existing lines run up to
  roughly 120 characters.

## Test-file organization

See [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for the full naming-convention
write-up. In short:

- One file per subject area, named `tests/test_<topic>.py`.
- Each `unittest.TestCase` subclass inside is named `<Subject>Tests`.
- Test methods are named `test_<snake_case_description>`, phrased as a
  behavior (for example `test_get_v1_entries_without_bearer_is_rejected`).
- [`tests/test_service_contract.py`](tests/test_service_contract.py) defines
  a storage-independent `ServiceContractTests` mixin plus one concrete
  `<Backend>ServiceContractTests` class per backend, so the same behavioral
  tests run against every `AuditLogService` implementation. When adding a
  new backend, add a new mixed-in class there rather than duplicating the
  contract tests.
- [`tests/test_serve.py`](tests/test_serve.py) exercises the real HTTP
  transport (a live `HTTPServer` bound to an OS-assigned loopback port),
  not a mock — new route behavior should be proven the same way.

## Commands for running the existing test suite

```bash
# Run the entire suite:
python3 -m unittest discover -s tests

# Run the entire suite with per-test names (verbose):
python3 -m unittest discover -s tests -v

# Run one test file:
python3 -m unittest tests.test_serve -v

# Run one test class:
python3 -m unittest tests.test_serve.ServeTransportTests -v

# Run one test method:
python3 -m unittest tests.test_serve.ServeTransportTests.test_health_is_public_and_returns_ok -v
```

No dependency installation or virtual environment is required first — the
suite uses only `unittest` and the standard library.

## Glossary of package and module names

- **`auditlog`** — the package
  ([`auditlog/__init__.py`](auditlog/__init__.py)): "Local compliance
  audit-log service used by the monitoring experiment." Declares
  `__version__`.
- **`auditlog.cli`** ([`auditlog/cli.py`](auditlog/cli.py)) — the
  command-line shell (`record` / `query` / `repair`). Depends only on the
  `AuditLogService` interface, the same contract an HTTP transport uses.
- **`auditlog.compat`** ([`auditlog/compat.py`](auditlog/compat.py)) — the
  compatibility reader that normalizes legacy (`store_version` 1) and
  current (`store_version` 2) log-store documents into one model.
- **`auditlog.errors`** ([`auditlog/errors.py`](auditlog/errors.py)) —
  exceptions raised at the boundary where external input becomes domain
  data (malformed actor, out-of-vocabulary outcome, a mismatched event id,
  a sequence gap, an unknown route).
- **`auditlog.integrity`** ([`auditlog/integrity.py`](auditlog/integrity.py))
  — shared integrity verification used by every backend's `repair`, so
  "what repair checks" is identical regardless of storage.
- **`auditlog.models`** ([`auditlog/models.py`](auditlog/models.py)) — the
  domain models: `AuditEvent`, the content-derived event-id rule, actor
  identity, the outcome vocabulary, timestamp parsing, and the
  factory/verification functions the stores use.
- **`auditlog.paths`** ([`auditlog/paths.py`](auditlog/paths.py)) — the
  request-path helpers (`canonical_path`, `auth_path`, `dispatch_path`)
  shared by authentication and dispatch, so a documented path and a
  harmless alternate spelling reach the same decision.
- **`auditlog.policy`** ([`auditlog/policy.py`](auditlog/policy.py)) —
  `Route` and `AccessPolicy` models: which canonical (method, path) pairs
  exist and which actor kinds hold which permissions.
- **`auditlog.reports`** ([`auditlog/reports.py`](auditlog/reports.py)) —
  resolves a caller-supplied report name to an actual file location beneath
  a store's own root, rejecting absolute paths or `..` escapes.
- **`auditlog.serve`** ([`auditlog/serve.py`](auditlog/serve.py)) — the
  loopback-only (`127.0.0.1`) HTTP transport around `AuditLogService`, with
  its own `ServeRoute` table (`/health`, `/v1/entries`, `/v1/integrity`,
  and their `/v2` aliases).
- **`auditlog.service`** ([`auditlog/service.py`](auditlog/service.py)) —
  the transport-agnostic `AuditLogService` interface that the CLI and the
  HTTP transport both call through, independent of storage backend.
- **`auditlog.sqlite_store`**
  ([`auditlog/sqlite_store.py`](auditlog/sqlite_store.py)) — the
  SQLite-backed, durable `AuditLogService` implementation; one file holds
  both the trail and its indexes.
- **`auditlog.store`** ([`auditlog/store.py`](auditlog/store.py)) — the
  JSON-file-backed `AuditLogService` implementation; append-only, with
  read-only support for the legacy archive format via `auditlog.compat`.
