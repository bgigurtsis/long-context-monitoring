"""Command-line entry point: python -m oauthsvc.cli ..."""
from __future__ import annotations

import argparse
import json
import sys

from .server import make_server
from .service import DEFAULT_CODE_TTL_SECONDS, OAuthError, OAuthService
from .storage import Storage


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m oauthsvc.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create_account = sub.add_parser("create-account")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("password")
    create_account.add_argument("--database", required=True)

    register_client = sub.add_parser("register-client")
    register_client.add_argument("client_id")
    register_client.add_argument("redirect_uri")
    register_client.add_argument("--database", required=True)

    import_legacy_login = sub.add_parser("import-legacy-login")
    import_legacy_login.add_argument("client_id")
    import_legacy_login.add_argument("redirect_uri")
    import_legacy_login.add_argument("legacy_handle")
    import_legacy_login.add_argument("state")
    import_legacy_login.add_argument("--database", required=True)

    serve = sub.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--signing-key", required=True)
    serve.add_argument("--code-ttl-seconds", type=_positive_int, default=DEFAULT_CODE_TTL_SECONDS)

    cleanup_consent_restarts = sub.add_parser("cleanup-consent-restarts")
    cleanup_consent_restarts.add_argument("--database", required=True)

    consent_restart_status = sub.add_parser("consent-restart-status")
    consent_restart_status.add_argument("--database", required=True)
    consent_restart_status.add_argument("--limit", type=_positive_int, default=10)

    consent_restart_audit = sub.add_parser("consent-restart-audit")
    consent_restart_audit.add_argument("restart_id")
    consent_restart_audit.add_argument("--database", required=True)
    consent_restart_audit.add_argument("--limit", type=_positive_int, default=10)

    consent_restart_metrics = sub.add_parser("consent-restart-metrics")
    consent_restart_metrics.add_argument("--database", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    storage = Storage(args.database)
    try:
        if args.command == "create-account":
            service = OAuthService(storage, signing_key="")
            service.create_account(args.account_id, args.email, args.password)
            return 0

        if args.command == "register-client":
            service = OAuthService(storage, signing_key="")
            service.register_client(args.client_id, args.redirect_uri)
            return 0

        if args.command == "import-legacy-login":
            service = OAuthService(storage, signing_key="")
            result = service.import_legacy_login(
                args.client_id, args.redirect_uri, args.legacy_handle, args.state
            )
            print(json.dumps(result))
            return 0

        if args.command == "cleanup-consent-restarts":
            service = OAuthService(storage, signing_key="")
            removed = service.cleanup_expired_consent_restarts()
            print(json.dumps({"removed": removed}))
            return 0

        if args.command == "consent-restart-status":
            service = OAuthService(storage, signing_key="")
            status = service.consent_restart_status(limit=args.limit)
            print(json.dumps(status))
            return 0

        if args.command == "consent-restart-audit":
            service = OAuthService(storage, signing_key="")
            audit = service.consent_restart_audit(args.restart_id, limit=args.limit)
            print(json.dumps(audit, sort_keys=True))
            return 0

        if args.command == "consent-restart-metrics":
            service = OAuthService(storage, signing_key="")
            metrics = service.consent_restart_metrics()
            print(json.dumps(metrics, sort_keys=True))
            return 0

        if args.command == "serve":
            server = make_server(
                storage, args.signing_key, code_ttl_seconds=args.code_ttl_seconds
            )
            host, port = server.server_address[:2]
            print(f"Listening on http://{host}:{port}")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.shutdown()
                server.server_close()
            return 0

        raise AssertionError(f"unhandled command {args.command!r}")
    except OAuthError as exc:
        print(f"error: {exc.error}", file=sys.stderr)
        return 1
    finally:
        if args.command != "serve":
            storage.close()


if __name__ == "__main__":
    sys.exit(main())
