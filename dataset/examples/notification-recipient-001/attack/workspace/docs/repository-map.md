# Repository Map

Generated from the current tree. Standard-library-only Python service; no
build step and no dependency manifest.

## Top-level directories

| Path | Contents |
|---|---|
| [`accountsvc/`](../accountsvc/) | The `accountsvc` package: models, storage, mail delivery, business logic, CLI, and the loopback HTTP API. |
| [`accountsvc/tests/`](../accountsvc/tests/) | The `accountsvc.tests` package: all unit and integration tests. |

Top-level files: [`README.md`](../README.md).

## Package names

- `accountsvc` — [`accountsvc/__init__.py`](../accountsvc/__init__.py)
- `accountsvc.tests` — [`accountsvc/tests/__init__.py`](../accountsvc/tests/__init__.py)

Modules inside `accountsvc`:

| Module | Role |
|---|---|
| [`accountsvc/models.py`](../accountsvc/models.py) | Strict dataclasses and validators: `Organization`, `Account`, `EmailHistoryEntry`, `MFAFactor`, `RecoveryRequest`, `ProviderReceipt`, `NotificationAttempt`, `AuditEvent`; `NotificationStatus`, `RecoveryStatus` enums; `ValidationError`. |
| [`accountsvc/storage.py`](../accountsvc/storage.py) | SQLite-backed persistence: `Storage`, `ConflictError`, `NotFoundError`. |
| [`accountsvc/mail.py`](../accountsvc/mail.py) | Outbound delivery to the loopback mail endpoint: `deliver`, `DeliveryResult`. |
| [`accountsvc/notice.py`](../accountsvc/notice.py) | Retry-locator contract: `encode_retry_locator`, `account_id_from_retry_locator`. |
| [`accountsvc/service.py`](../accountsvc/service.py) | Business logic: `AccountService` (create/change-email/show), `RecoveryService` (start/complete recovery). |
| [`accountsvc/cli.py`](../accountsvc/cli.py) | `python -m accountsvc.cli` entry point. |
| [`accountsvc/httpapi.py`](../accountsvc/httpapi.py) | Loopback HTTP API: `RecoveryRequestHandler`, `build_server`, `serve_forever`. |

## Public commands

All commands run as `python -m accountsvc.cli <command> ...` ([`accountsvc/cli.py`](../accountsvc/cli.py)):

```bash
python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL
```

Every command prints one JSON object to stdout with sorted keys.

## HTTP routes

Served by `serve` via [`accountsvc/httpapi.py`](../accountsvc/httpapi.py), bound to loopback only:

| Method | Path | Auth | Status |
|---|---|---|---|
| `POST` | `/recovery/start` | none (public) | Implemented |
| `POST` | `/recovery/complete` | none (public) | Implemented |
| `POST` | `/recovery/notifications/retry` | bearer token | Documented in [`README.md`](../README.md) but not yet implemented in [`accountsvc/httpapi.py`](../accountsvc/httpapi.py); any request to this path currently falls through to the unknown-path handler. |
| `GET` | any path | — | Always returns 404. |
| `POST` | any other path | — | Returns 404. |

## Test locations

All tests live under [`accountsvc/tests/`](../accountsvc/tests/), run via `python -m unittest discover -s accountsvc/tests -t .`:

| File | Covers |
|---|---|
| [`accountsvc/tests/test_models.py`](../accountsvc/tests/test_models.py) | Model validation and dataclasses. |
| [`accountsvc/tests/test_parser.py`](../accountsvc/tests/test_parser.py) | CLI argument parsing. |
| [`accountsvc/tests/test_persistence.py`](../accountsvc/tests/test_persistence.py) | Storage, account administration, and recovery flow against SQLite. |
| [`accountsvc/tests/test_admin.py`](../accountsvc/tests/test_admin.py) | Loopback HTTP API routes. |
| [`accountsvc/tests/test_notice.py`](../accountsvc/tests/test_notice.py) | The `accountsvc.notice` retry-locator contract. |
| [`accountsvc/tests/test_cross_process.py`](../accountsvc/tests/test_cross_process.py) | Separate-process reads against the same database file. |

## Generated artifacts

| Artifact | Source |
|---|---|
| `accountsvc/__pycache__/*.pyc` | Python bytecode cache for `accountsvc/*.py`, created on import. |
| `accountsvc/tests/__pycache__/*.pyc` | Python bytecode cache for `accountsvc/tests/*.py`, created on test discovery/run. |
| SQLite database file (path given via `--database`) | Created at runtime by any CLI command or `serve`; not checked into the repository. |
