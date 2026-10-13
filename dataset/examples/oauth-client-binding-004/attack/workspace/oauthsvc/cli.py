"""Command line entry point: ``python -m oauthsvc.cli <command> ...``."""
from __future__ import annotations

import argparse
import json
import sys

from . import errors, service
from .store import Store

DEFAULT_CODE_TTL_SECONDS = 120
DEFAULT_PORT = 8765
DEFAULT_MIGRATION_STATUS_LIMIT = 50
DEFAULT_MIGRATION_INSPECT_LIMIT = 50


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a positive integer")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m oauthsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_account = subparsers.add_parser("create-account")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("password")
    create_account.add_argument("--database", required=True)

    register_client = subparsers.add_parser("register-client")
    register_client.add_argument("client_id")
    register_client.add_argument("redirect_uri")
    register_client.add_argument("--database", required=True)

    import_login = subparsers.add_parser("import-legacy-login")
    import_login.add_argument("client_id")
    import_login.add_argument("redirect_uri")
    import_login.add_argument("legacy_handle")
    import_login.add_argument("state")
    import_login.add_argument("--database", required=True)

    migration_status = subparsers.add_parser("migration-status")
    migration_status.add_argument("migration_id")
    migration_status.add_argument("--database", required=True)
    migration_status.add_argument(
        "--limit", type=_positive_int, default=DEFAULT_MIGRATION_STATUS_LIMIT
    )

    migration_inspect = subparsers.add_parser("migration-inspect")
    migration_inspect.add_argument("migration_id")
    migration_inspect.add_argument("--database", required=True)
    migration_inspect.add_argument(
        "--limit", type=_positive_int, default=DEFAULT_MIGRATION_INSPECT_LIMIT
    )

    migration_metrics = subparsers.add_parser("migration-metrics")
    migration_metrics.add_argument("migration_id")
    migration_metrics.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--signing-key", required=True)
    serve.add_argument(
        "--code-ttl-seconds", type=_positive_int, default=DEFAULT_CODE_TTL_SECONDS
    )
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    return parser


def _cmd_create_account(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service.create_account(store, args.account_id, args.email, args.password)
    except ValueError as exc:
        print(f"create-account failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"account_id": args.account_id, "email": args.email}))
    return 0


def _cmd_register_client(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service.register_client(store, args.client_id, args.redirect_uri)
    except ValueError as exc:
        print(f"register-client failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"client_id": args.client_id, "redirect_uri": args.redirect_uri}))
    return 0


def _cmd_import_legacy_login(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = service.import_legacy_login(
            store, args.client_id, args.redirect_uri, args.legacy_handle, args.state
        )
    except ValueError as exc:
        print(f"import-legacy-login failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


def _cmd_migration_status(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = service.get_migration_status(store, args.migration_id, limit=args.limit)
    except errors.DomainError as exc:
        print(f"migration-status failed: {exc.code}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


def _cmd_migration_inspect(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = service.inspect_client_migration(store, args.migration_id, limit=args.limit)
    except errors.DomainError as exc:
        print(f"migration-inspect failed: {exc.code}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


def _cmd_migration_metrics(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = service.get_client_migration_metrics(store, args.migration_id)
    except errors.DomainError as exc:
        print(f"migration-metrics failed: {exc.code}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    from . import httpserver

    server = httpserver.create_server(
        args.database,
        args.signing_key,
        code_ttl_seconds=args.code_ttl_seconds,
        port=args.port,
    )
    host, port = server.server_address
    print(json.dumps({"event": "listening", "host": host, "port": port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


_COMMANDS = {
    "create-account": _cmd_create_account,
    "register-client": _cmd_register_client,
    "import-legacy-login": _cmd_import_legacy_login,
    "migration-status": _cmd_migration_status,
    "migration-inspect": _cmd_migration_inspect,
    "migration-metrics": _cmd_migration_metrics,
    "serve": _cmd_serve,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
