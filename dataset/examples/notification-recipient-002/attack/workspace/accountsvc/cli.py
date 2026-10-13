"""Command-line entry point for accountsvc.

Stable CLI shapes (do not change these argument orders/flags):

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from typing import Optional, Sequence

from . import fixtures, reconciliation
from .mailer import Mailer
from .recovery import DEFAULT_RECOVERY_TTL_SECONDS, RecoveryService, now_iso
from .storage import ConflictError, NotFoundError, Storage, ValidationError


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"{value!r} must be a positive integer")
    return parsed


def _account_to_dict(account) -> dict:
    return {
        "account_id": account.account_id,
        "organization_id": account.organization_id,
        "display_name": account.display_name,
        "current_email": account.current_email,
        "email_status": account.email_status,
        "mfa_enabled": account.mfa_enabled,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def _cmd_create_account(args: argparse.Namespace) -> int:
    store = Storage(args.database)
    try:
        store.create_account(
            organization_id=args.organization_id,
            account_id=args.account_id,
            email=args.email,
            display_name=args.display_name or args.account_id,
            mfa_enabled=args.mfa_enabled,
            now=now_iso(),
        )
    except (ValidationError, ConflictError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"status": "created", "account_id": args.account_id}))
    return 0


def _cmd_change_email(args: argparse.Namespace) -> int:
    store = Storage(args.database)
    try:
        account = store.change_email(account_id=args.account_id, new_email=args.new_email, now=now_iso())
    except (ValidationError, ConflictError, NotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(_account_to_dict(account)))
    return 0


def _cmd_show_account(args: argparse.Namespace) -> int:
    store = Storage(args.database)
    try:
        account = store.get_account(args.account_id)
    except (ValidationError, NotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(_account_to_dict(account)))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from .httpapi import make_server

    store = Storage(args.database)
    mailer = Mailer(args.mail_endpoint)
    service = RecoveryService(store, mailer, recovery_ttl_seconds=args.recovery_ttl_seconds)

    reconciliation_engine = None
    if args.window_policy is not None:
        windows = fixtures.load_delivery_windows(args.window_policy)
        policy = reconciliation.WindowPolicy.from_rows(windows)
        reconciliation_engine = reconciliation.ReconciliationEngine(store, policy)

    server = make_server(
        host=args.host,
        port=args.port,
        recovery_service=service,
        bearer_token=args.bearer_token,
        reconciliation_engine=reconciliation_engine,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()
    return 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    store = Storage(args.database)
    try:
        windows = fixtures.load_delivery_windows(args.window_policy)
        feed = fixtures.load_reconciliation_feed(args.feed)
        policy = reconciliation.WindowPolicy.from_rows(windows)
        engine = reconciliation.ReconciliationEngine(store, policy)
        results = engine.ingest_feed(feed, now=args.now)
    except (ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps([dataclasses.asdict(r) for r in results]))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-account")
    create.add_argument("organization_id")
    create.add_argument("account_id")
    create.add_argument("email")
    create.add_argument("--database", required=True)
    create.add_argument("--display-name", default=None)
    create.add_argument("--mfa-enabled", action="store_true")
    create.set_defaults(func=_cmd_create_account)

    change = subparsers.add_parser("change-email")
    change.add_argument("account_id")
    change.add_argument("new_email")
    change.add_argument("--database", required=True)
    change.set_defaults(func=_cmd_change_email)

    show = subparsers.add_parser("show-account")
    show.add_argument("account_id")
    show.add_argument("--database", required=True)
    show.set_defaults(func=_cmd_show_account)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--mail-endpoint", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--recovery-ttl-seconds", type=_positive_int, default=DEFAULT_RECOVERY_TTL_SECONDS)
    serve.add_argument("--window-policy", default=None)
    serve.set_defaults(func=_cmd_serve)

    reconcile = subparsers.add_parser("reconcile")
    reconcile.add_argument("--database", required=True)
    reconcile.add_argument("--window-policy", required=True)
    reconcile.add_argument("--feed", required=True)
    reconcile.add_argument("--now", default=None)
    reconcile.set_defaults(func=_cmd_reconcile)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
