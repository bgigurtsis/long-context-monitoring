"""Command-line entrypoint. `create-account`, `change-email`, `show-account`,
and `serve` keep the exact shapes documented in the starter README; every
other subcommand is additive.
"""
from __future__ import annotations

import argparse
import signal
import sys

from . import db, jsonutil, security, service
from .errors import ServiceError


def _print_result(payload: dict) -> None:
    sys.stdout.write(jsonutil.dumps(payload, pretty=True))


def _print_error(exc: ServiceError) -> None:
    sys.stderr.write(jsonutil.dumps({"error": exc.code, "message": exc.message}, pretty=True))


def _run(func) -> int:
    try:
        _print_result(func())
        return 0
    except ServiceError as exc:
        _print_error(exc)
        return 1


def cmd_create_account(args: argparse.Namespace) -> int:
    conn = db.connect(args.database)
    try:
        return _run(lambda: service.create_account(conn, args.organization_id, args.account_id, args.email))
    finally:
        conn.close()


def cmd_change_email(args: argparse.Namespace) -> int:
    conn = db.connect(args.database)
    try:
        return _run(lambda: service.change_email(conn, args.account_id, args.new_email))
    finally:
        conn.close()


def cmd_show_account(args: argparse.Namespace) -> int:
    conn = db.connect(args.database)
    try:
        return _run(lambda: service.show_account(conn, args.account_id))
    finally:
        conn.close()


def cmd_enroll_mfa(args: argparse.Namespace) -> int:
    conn = db.connect(args.database)
    try:
        return _run(lambda: service.enroll_mfa(conn, args.account_id))
    finally:
        conn.close()


def cmd_list_accounts(args: argparse.Namespace) -> int:
    conn = db.connect(args.database)
    try:
        return _run(lambda: service.list_accounts(conn, args.organization_id))
    finally:
        conn.close()


def cmd_serve(args: argparse.Namespace) -> int:
    from . import httpapi

    server = httpapi.create_server(
        args.host,
        args.port,
        args.database,
        args.bearer_token,
        args.mail_endpoint,
        args.recovery_token_ttl_seconds,
        clock_now=args.clock_now,
    )
    host, port = server.server_address[:2]
    sys.stdout.write(jsonutil.dumps({"listening": True, "host": host, "port": port}, pretty=True))
    sys.stdout.flush()

    def _shutdown(signum, frame):
        server.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-account")
    p.add_argument("organization_id")
    p.add_argument("account_id")
    p.add_argument("email")
    p.add_argument("--database", required=True)
    p.set_defaults(func=cmd_create_account)

    p = sub.add_parser("change-email")
    p.add_argument("account_id")
    p.add_argument("new_email")
    p.add_argument("--database", required=True)
    p.set_defaults(func=cmd_change_email)

    p = sub.add_parser("show-account")
    p.add_argument("account_id")
    p.add_argument("--database", required=True)
    p.set_defaults(func=cmd_show_account)

    p = sub.add_parser("enroll-mfa")
    p.add_argument("account_id")
    p.add_argument("--database", required=True)
    p.set_defaults(func=cmd_enroll_mfa)

    p = sub.add_parser("list-accounts")
    p.add_argument("organization_id")
    p.add_argument("--database", required=True)
    p.set_defaults(func=cmd_list_accounts)

    p = sub.add_parser("serve")
    p.add_argument("--database", required=True)
    p.add_argument("--bearer-token", required=True)
    p.add_argument("--mail-endpoint", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--recovery-token-ttl-seconds", type=float, default=security.TOKEN_TTL_SECONDS)
    p.add_argument(
        "--clock-now",
        type=float,
        default=None,
        help="Freeze the server's clock at this epoch-seconds value instead of the real wall clock.",
    )
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
