"""Command-line entry point for the account recovery service."""
from __future__ import annotations

import argparse
import datetime as _dt
import sys

from . import httpapi, service, storage
from .errors import ServiceError
from .jsonutil import dumps


def _print_json(payload: dict) -> None:
    print(dumps(payload))


def _cmd_create_account(args: argparse.Namespace) -> int:
    with storage.connect(args.database) as conn:
        result = service.create_account(conn, args.organization_id, args.account_id, args.email)
    _print_json(result)
    return 0


def _cmd_change_email(args: argparse.Namespace) -> int:
    with storage.connect(args.database) as conn:
        result = service.change_email(conn, args.account_id, args.new_email)
    _print_json(result)
    return 0


def _cmd_show_account(args: argparse.Namespace) -> int:
    with storage.connect(args.database) as conn:
        result = service.show_account(conn, args.account_id)
    _print_json(result)
    return 0


def _parse_clock_now(value):
    if value is None:
        return None
    moment = _dt.datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_dt.timezone.utc)
    return moment


def _cmd_serve(args: argparse.Namespace) -> int:
    clock_now = _parse_clock_now(args.clock_now)
    recovery_token_ttl = (
        _dt.timedelta(seconds=args.recovery_token_ttl_seconds)
        if args.recovery_token_ttl_seconds is not None
        else None
    )
    httpd = httpapi.serve(
        args.database, args.bearer_token, args.mail_endpoint, args.host, args.port,
        clock_now=clock_now, recovery_token_ttl=recovery_token_ttl,
    )
    host, port = httpd.server_address
    print(f"listening on {host}:{port}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-account")
    create.add_argument("organization_id")
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
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument(
        "--clock-now", default=None,
        help="ISO 8601 timestamp to use as this process's fixed clock (default: real system clock); "
             "for deterministic expiry tests",
    )
    serve.add_argument(
        "--recovery-token-ttl-seconds", type=int, default=None,
        help="override the recovery token TTL, in seconds (default: 1800); for deterministic expiry tests",
    )
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ServiceError as exc:
        print(dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
