"""Command line interface for the account recovery service."""
from __future__ import annotations

import argparse
import json
import sys

from . import storage
from .server import make_server
from .service import RecoveryService


def _cmd_create_account(args: argparse.Namespace) -> int:
    service = RecoveryService(args.database, mail_endpoint="")
    try:
        service.create_account(args.org_id, args.account_id, args.email)
    except (storage.AccountExistsError, storage.EmailInUseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"created {args.account_id}")
    return 0


def _cmd_change_email(args: argparse.Namespace) -> int:
    service = RecoveryService(args.database, mail_endpoint="")
    try:
        service.change_email(args.account_id, args.new_email)
    except (storage.AccountNotFoundError, storage.EmailInUseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"updated {args.account_id}")
    return 0


def _cmd_show_account(args: argparse.Namespace) -> int:
    service = RecoveryService(args.database, mail_endpoint="")
    account = service.show_account(args.account_id)
    if account is None:
        print(f"error: no such account {args.account_id}", file=sys.stderr)
        return 1
    print(json.dumps(account))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    service = RecoveryService(args.database, mail_endpoint=args.mail_endpoint)
    server = make_server(service, args.bearer_token, port=args.port)
    host, port = server.server_address[:2]
    print(f"listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-account")
    create.add_argument("org_id")
    create.add_argument("account_id")
    create.add_argument("email")
    create.add_argument("--database", required=True)
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
    serve.add_argument("--port", type=int, default=0)
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
