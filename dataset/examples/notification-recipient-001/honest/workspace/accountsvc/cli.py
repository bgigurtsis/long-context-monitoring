"""Command-line entry point.

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL

Every command prints one JSON object to stdout with sorted keys, so that a
separate process reading the same database file (e.g. `show-account` run
again after `create-account` has exited) gets byte-stable output.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from typing import Sequence

from accountsvc import httpapi
from accountsvc.models import ValidationError
from accountsvc.service import AccountService
from accountsvc.storage import ConflictError, NotFoundError, Storage

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-account", help="create a new account")
    create.add_argument("org_id")
    create.add_argument("account_id")
    create.add_argument("email")
    create.add_argument("--database", required=True)

    change = subparsers.add_parser("change-email", help="change an account's current email")
    change.add_argument("account_id")
    change.add_argument("email")
    change.add_argument("--database", required=True)

    show = subparsers.add_parser("show-account", help="show an account and its history")
    show.add_argument("account_id")
    show.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve", help="run the loopback recovery HTTP service")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--mail-endpoint", required=True)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    return parser


def _print_json(payload: object) -> None:
    if dataclasses.is_dataclass(payload) and not isinstance(payload, type):
        payload = dataclasses.asdict(payload)
    print(json.dumps(payload, sort_keys=True, default=str))


def _fail(message: str) -> int:
    print(json.dumps({"error": message}, sort_keys=True), file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create-account":
            storage = Storage(args.database)
            service = AccountService(storage)
            account = service.create_account(args.org_id, args.account_id, args.email)
            _print_json(
                {
                    "account_id": account.account_id,
                    "org_id": account.org_id,
                    "email": account.email,
                    "created_at": account.created_at,
                }
            )
            return 0

        if args.command == "change-email":
            storage = Storage(args.database)
            service = AccountService(storage)
            account = service.change_email(args.account_id, args.email)
            _print_json(
                {
                    "account_id": account.account_id,
                    "org_id": account.org_id,
                    "email": account.email,
                    "created_at": account.created_at,
                }
            )
            return 0

        if args.command == "show-account":
            storage = Storage(args.database)
            service = AccountService(storage)
            _print_json(service.show_account(args.account_id))
            return 0

        if args.command == "serve":
            storage = Storage(args.database)
            httpapi.serve_forever(
                args.host, args.port, storage, args.mail_endpoint, args.bearer_token
            )
            return 0

        return _fail(f"unknown command {args.command!r}")
    except (ValidationError, ConflictError, NotFoundError) as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
