"""Command-line entry points for the loopback OAuth service."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import security
from .db import Database
from .service import OAuthService
from .server import run_server


def _cmd_create_account(args: argparse.Namespace) -> int:
    db = Database(args.database)
    salt_hex, hash_hex = security.hash_password(args.password)
    try:
        db.create_account(args.account_id, args.email, salt_hex, hash_hex)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


def _cmd_register_client(args: argparse.Namespace) -> int:
    db = Database(args.database)
    try:
        db.register_client(args.client_id, args.redirect_uri)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


def _cmd_import_legacy_login(args: argparse.Namespace) -> int:
    db = Database(args.database)
    try:
        client = db.get_client(args.client_id)
        if client is None or client["redirect_uri"] != args.redirect_uri:
            print("error: unregistered_callback", file=sys.stderr)
            return 1

        login_id = security.new_opaque_id()
        recovery_locator = security.new_opaque_id()

        db.create_pending_login(
            login_id, args.client_id, args.redirect_uri, args.state, kind="continuation"
        )
        try:
            db.import_legacy_login(args.client_id, args.legacy_handle, login_id, recovery_locator)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        result = {
            "client_id": args.client_id,
            "login_id": login_id,
            "resume_reference": {
                "kind": "continuation",
                "client_id": args.client_id,
                "value": login_id,
            },
        }
        print(json.dumps(result))
    finally:
        db.close()
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    db = Database(args.database)
    service = OAuthService(db, args.signing_key)
    httpd = run_server(service, args.host, args.port)
    host, port = httpd.server_address[:2]
    print(json.dumps({"host": host, "port": port, "pid": os.getpid()}), flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        db.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m oauthsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_account = subparsers.add_parser("create-account")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("password")
    create_account.add_argument("--database", required=True)
    create_account.set_defaults(func=_cmd_create_account)

    register_client = subparsers.add_parser("register-client")
    register_client.add_argument("client_id")
    register_client.add_argument("redirect_uri")
    register_client.add_argument("--database", required=True)
    register_client.set_defaults(func=_cmd_register_client)

    import_legacy = subparsers.add_parser("import-legacy-login")
    import_legacy.add_argument("client_id")
    import_legacy.add_argument("redirect_uri")
    import_legacy.add_argument("legacy_handle")
    import_legacy.add_argument("state")
    import_legacy.add_argument("--database", required=True)
    import_legacy.set_defaults(func=_cmd_import_legacy_login)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--signing-key", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
