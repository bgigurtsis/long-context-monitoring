"""Command-line interface for the OAuth authorization-code import service.

Keeps the documented CLI shapes stable::

    python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
    python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
    python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
    python -m oauthsvc.cli import-batch-status BATCH_ID --database STATE.db
    python -m oauthsvc.cli import-receipt BATCH_ID ROW_INDEX --database STATE.db
    python -m oauthsvc.cli import-completion-receipt IMPORT_ID --database STATE.db
    python -m oauthsvc.cli serve --database STATE.db --signing-key KEY
"""
from __future__ import annotations

import argparse
import json
import sys

from .httpapi import make_server
from .service import DEFAULT_CODE_TTL_SECONDS, OAuthService, ServiceError
from .storage import Store


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("--code-ttl-seconds must be a positive integer")
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

    batch_status = subparsers.add_parser("import-batch-status")
    batch_status.add_argument("batch_id")
    batch_status.add_argument("--database", required=True)

    receipt = subparsers.add_parser("import-receipt")
    receipt.add_argument("batch_id")
    receipt.add_argument("row_index", type=int)
    receipt.add_argument("--database", required=True)

    completion_receipt = subparsers.add_parser("import-completion-receipt")
    completion_receipt.add_argument("import_id")
    completion_receipt.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--signing-key", required=True)
    serve.add_argument("--code-ttl-seconds", type=_positive_int, default=DEFAULT_CODE_TTL_SECONDS)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-account":
        return _create_account(args)
    if args.command == "register-client":
        return _register_client(args)
    if args.command == "import-legacy-login":
        return _import_legacy_login(args)
    if args.command == "import-batch-status":
        return _import_batch_status(args)
    if args.command == "import-receipt":
        return _import_receipt(args)
    if args.command == "import-completion-receipt":
        return _import_completion_receipt(args)
    if args.command == "serve":
        return _serve(args)
    return 1


def _create_account(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        created = service.create_account(args.account_id, args.email, args.password)
    finally:
        store.close()
    if not created:
        print(f"account already exists: {args.account_id}", file=sys.stderr)
        return 1
    print(json.dumps({"account_id": args.account_id}))
    return 0


def _register_client(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        created = service.register_client(args.client_id, args.redirect_uri)
    finally:
        store.close()
    if not created:
        print(f"client already registered: {args.client_id}", file=sys.stderr)
        return 1
    print(json.dumps({"client_id": args.client_id, "redirect_uri": args.redirect_uri}))
    return 0


def _import_legacy_login(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        try:
            result = service.import_legacy_login(
                args.client_id, args.redirect_uri, args.legacy_handle, args.state
            )
        except ServiceError as exc:
            print(f"import failed: {exc.error}", file=sys.stderr)
            return 1
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _import_batch_status(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        try:
            result = service.get_batch_status(args.batch_id)
        except ServiceError as exc:
            print(f"batch status failed: {exc.error}", file=sys.stderr)
            return 1
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _import_receipt(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        try:
            result = service.get_import_receipt(args.batch_id, args.row_index)
        except ServiceError as exc:
            print(f"receipt lookup failed: {exc.error}", file=sys.stderr)
            return 1
    finally:
        store.close()
    print(json.dumps(result, sort_keys=True))
    return 0


def _import_completion_receipt(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        service = OAuthService(store, signing_key="")
        try:
            result = service.get_completion_receipt(args.import_id)
        except ServiceError as exc:
            print(f"completion receipt lookup failed: {exc.error}", file=sys.stderr)
            return 1
    finally:
        store.close()
    print(json.dumps(result, sort_keys=True))
    return 0


def _serve(args: argparse.Namespace) -> int:
    store = Store(args.database)
    service = OAuthService(
        store, signing_key=args.signing_key, code_ttl_seconds=args.code_ttl_seconds
    )
    server = make_server(args.host, args.port, service)
    print(server.server_address[1])
    sys.stdout.flush()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
