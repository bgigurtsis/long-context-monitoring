"""Command-line entry point for the account recovery service.

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL
    python -m accountsvc.cli import-legacy-envelopes ENVELOPES.jsonl --server URL --bearer-token TOKEN
    python -m accountsvc.cli run-legacy-batch --accounts A.yaml --envelopes E.jsonl --manifest M.txt --database STATE.db
    python -m accountsvc.cli migration-status BATCH_LABEL --database STATE.db
    python -m accountsvc.cli verify-migration BATCH_LABEL --database STATE.db

These four shapes are stable; new functionality is added as new subcommands
rather than by changing them. ``import-legacy-envelopes`` is one such
addition: it authenticates to a running ``serve`` process's admin route
the same way any other administrative caller would, rather than writing to
the database file directly. ``run-legacy-batch``, ``migration-status``, and
``verify-migration`` are three more: like ``create-account``/``show-account``,
they open the database file directly rather than going over HTTP, since
durably classifying a legacy batch and reading back its status or
verification report are the same kind of direct administrative operation.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import timedelta

from .errors import AccountServiceError, ValidationError
from .httpserver import build_server
from .legacy_import import load_legacy_envelopes, load_stonebridge_accounts
from .migration_batch import (
    build_migration_status_report,
    build_migration_verification_report,
    run_durable_legacy_batch,
)
from .recovery import RecoveryService
from .storage import Storage
from .validate import validate_email, validate_id


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{raw!r} must be a positive integer")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-account", help="Create an account with its initial current email address")
    create.add_argument("organization_id")
    create.add_argument("account_id")
    create.add_argument("email")
    create.add_argument("--database", required=True)

    change = subparsers.add_parser("change-email", help="Release the current email and claim a new one")
    change.add_argument("account_id")
    change.add_argument("new_email")
    change.add_argument("--database", required=True)

    show = subparsers.add_parser("show-account", help="Print an account's current state as JSON")
    show.add_argument("account_id")
    show.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve", help="Run the loopback recovery HTTP service")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True, help="Token required to call the notifications retry route")
    serve.add_argument("--mail-endpoint", required=True, help="URL of the loopback mail endpoint")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument(
        "--recovery-ttl-seconds",
        type=_positive_int,
        default=900,
        help="Lifetime, in seconds, assigned to a token when /recovery/start creates it (default: 900)",
    )

    import_cmd = subparsers.add_parser(
        "import-legacy-envelopes",
        help="Import a batch of versioned legacy receipt envelope wrappers via the authenticated admin route",
    )
    import_cmd.add_argument("envelopes_file", help="Path to a JSONL file of envelope wrapper records")
    import_cmd.add_argument("--server", required=True, help="Base URL of a running `serve` process, e.g. http://127.0.0.1:8765")
    import_cmd.add_argument("--bearer-token", required=True)

    run_batch = subparsers.add_parser(
        "run-legacy-batch",
        help="Durably classify and import a stonebridge legacy-envelope batch, resuming any interrupted prior run",
    )
    run_batch.add_argument("--accounts", required=True, help="Path to the stonebridge account seed YAML fixture")
    run_batch.add_argument("--envelopes", required=True, help="Path to the legacy receipt envelopes JSONL file")
    run_batch.add_argument(
        "--manifest", required=True, help="Path to a text file of envelope ids to migrate, one per line, in order"
    )
    run_batch.add_argument("--database", required=True)
    run_batch.add_argument("--batch-label", default="legacy-batch-s04")

    status = subparsers.add_parser(
        "migration-status", help="Print the durable migration status report for a batch label as JSON"
    )
    status.add_argument("batch_label")
    status.add_argument("--database", required=True)

    verify = subparsers.add_parser(
        "verify-migration",
        help="Print a redacted migration verification report for a batch label as JSON",
    )
    verify.add_argument("batch_label")
    verify.add_argument("--database", required=True)

    return parser


def _account_to_dict(account) -> dict:
    return {
        "account_id": account.account_id,
        "organization_id": account.organization_id,
        "current_email": account.current_email,
        "mfa_enabled": account.mfa_enabled,
        "created_at": account.created_at,
    }


def _cmd_create_account(args: argparse.Namespace) -> int:
    validate_id(args.organization_id, "organization_id")
    validate_id(args.account_id, "account_id")
    validate_email(args.email)
    with Storage(args.database) as storage:
        account = storage.create_account(args.organization_id, args.account_id, args.email)
    print(json.dumps(_account_to_dict(account)))
    return 0


def _cmd_change_email(args: argparse.Namespace) -> int:
    validate_id(args.account_id, "account_id")
    validate_email(args.new_email)
    with Storage(args.database) as storage:
        account = storage.change_email(args.account_id, args.new_email)
    print(json.dumps(_account_to_dict(account)))
    return 0


def _cmd_show_account(args: argparse.Namespace) -> int:
    validate_id(args.account_id, "account_id")
    with Storage(args.database) as storage:
        account = storage.get_account(args.account_id)
    if account is None:
        print(json.dumps({"error": f"account {args.account_id} not found"}), file=sys.stderr)
        return 1
    print(json.dumps(_account_to_dict(account)))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    storage = Storage(args.database)
    recovery_service = RecoveryService(
        storage,
        mail_endpoint=args.mail_endpoint,
        token_ttl=timedelta(seconds=args.recovery_ttl_seconds),
    )
    server = build_server(args.host, args.port, recovery_service, args.bearer_token, storage)
    try:
        print(f"accountsvc listening on http://{args.host}:{args.port}")
        server.serve_forever()
    finally:
        server.server_close()
        storage.close()
    return 0


def _cmd_import_legacy_envelopes(args: argparse.Namespace) -> int:
    records = []
    with open(args.envelopes_file, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    body = json.dumps({"envelopes": records}).encode("utf-8")
    request = urllib.request.Request(
        args.server.rstrip("/") + "/admin/legacy-envelopes/import",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.bearer_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(response.read().decode("utf-8"))
            return 0
    except urllib.error.HTTPError as exc:
        with exc:
            print(exc.read().decode("utf-8"), file=sys.stderr)
        return 1


def _cmd_run_legacy_batch(args: argparse.Namespace) -> int:
    accounts, _ = load_stonebridge_accounts(args.accounts)
    envelopes = load_legacy_envelopes(args.envelopes)
    envelope_ids = []
    with open(args.manifest, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                envelope_ids.append(line)

    with Storage(args.database) as storage:
        results = run_durable_legacy_batch(storage, envelope_ids, accounts, envelopes, batch_label=args.batch_label)
    print(json.dumps({"results": results}))
    return 0


def _cmd_migration_status(args: argparse.Namespace) -> int:
    with Storage(args.database) as storage:
        report = build_migration_status_report(storage, args.batch_label)
    print(json.dumps(report))
    return 0


def _cmd_verify_migration(args: argparse.Namespace) -> int:
    with Storage(args.database) as storage:
        report = build_migration_verification_report(storage, args.batch_label)
    print(json.dumps(report))
    return 0


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "create-account": _cmd_create_account,
        "change-email": _cmd_change_email,
        "show-account": _cmd_show_account,
        "serve": _cmd_serve,
        "import-legacy-envelopes": _cmd_import_legacy_envelopes,
        "run-legacy-batch": _cmd_run_legacy_batch,
        "migration-status": _cmd_migration_status,
        "verify-migration": _cmd_verify_migration,
    }
    try:
        return handlers[args.command](args)
    except ValidationError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    except AccountServiceError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
