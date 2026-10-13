"""Command-line entry point for the account recovery service.

::

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL

These four shapes are the stable contract; new flags may only ever be
optional additions. ``serve`` additionally accepts ``--recovery-ttl-seconds
SECONDS`` (a positive integer, default 900) that sets the lifetime of newly
created recovery tokens; it never affects tokens already persisted in the
database.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .errors import AccountServiceError
from .httpd import create_server
from .service import RECOVERY_TOKEN_TTL_SECONDS, AccountService
from .storage import Storage

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{raw!r} must be a positive integer")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_account = subparsers.add_parser("create-account", help="create an account owning an email")
    create_account.add_argument("organization_id")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("--database", required=True)

    change_email = subparsers.add_parser("change-email", help="release the current email and claim a new one")
    change_email.add_argument("account_id")
    change_email.add_argument("new_email")
    change_email.add_argument("--database", required=True)

    show_account = subparsers.add_parser("show-account", help="print account state and email history")
    show_account.add_argument("account_id")
    show_account.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve", help="run the loopback recovery HTTP service")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--mail-endpoint", required=True)
    serve.add_argument("--host", default=DEFAULT_HOST, choices=["127.0.0.1", "::1", "localhost"])
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--recovery-ttl-seconds", type=_positive_int, default=RECOVERY_TOKEN_TTL_SECONDS)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create-account":
            with Storage(args.database) as storage:
                result = AccountService(storage).create_account(
                    args.organization_id, args.account_id, args.email
                )
            _print_json(result)
        elif args.command == "change-email":
            with Storage(args.database) as storage:
                result = AccountService(storage).change_email(args.account_id, args.new_email)
            _print_json(result)
        elif args.command == "show-account":
            with Storage(args.database) as storage:
                result = AccountService(storage).show_account(args.account_id)
            _print_json(result)
        elif args.command == "serve":
            return _serve(args)
        else:  # pragma: no cover - argparse enforces valid choices
            parser.error(f"unknown command {args.command!r}")
    except AccountServiceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _serve(args: argparse.Namespace) -> int:
    with Storage(args.database) as storage:
        service = AccountService(
            storage, mail_endpoint=args.mail_endpoint, recovery_ttl_seconds=args.recovery_ttl_seconds
        )
        server = create_server(args.host, args.port, service, args.bearer_token)
        bound_host, bound_port = server.server_address[:2]
        print(f"serving on http://{bound_host}:{bound_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    return 0


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
