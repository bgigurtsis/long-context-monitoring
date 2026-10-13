"""Command-line entry point for the OAuth authorization-code service.

Documented shapes (kept stable):

    python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
    python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
    python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
    python -m oauthsvc.cli serve --database STATE.db --signing-key KEY
    python -m oauthsvc.cli claim-stale-recovery --database STATE.db [--lease-seconds N]
    python -m oauthsvc.cli complete-recovery-cleanup RECOVERY_ID CLAIM_TOKEN --database STATE.db
    python -m oauthsvc.cli recovery-status --database STATE.db
    python -m oauthsvc.cli inspect-recovery RECOVERY_ID --database STATE.db
    python -m oauthsvc.cli recovery-stage-metrics --database STATE.db
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .httpd import create_server
from .service import DEFAULT_CODE_TTL_SECONDS, DEFAULT_RECOVERY_LEASE_SECONDS, OAuthService, ServiceError
from .store import Store


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _build_parser() -> argparse.ArgumentParser:
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

    import_legacy = subparsers.add_parser("import-legacy-login")
    import_legacy.add_argument("client_id")
    import_legacy.add_argument("redirect_uri")
    import_legacy.add_argument("legacy_handle")
    import_legacy.add_argument("state")
    import_legacy.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--signing-key", required=True)
    serve.add_argument("--code-ttl-seconds", type=_positive_int, default=DEFAULT_CODE_TTL_SECONDS)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)

    claim_stale_recovery = subparsers.add_parser("claim-stale-recovery")
    claim_stale_recovery.add_argument("--database", required=True)
    claim_stale_recovery.add_argument(
        "--lease-seconds", type=_positive_int, default=DEFAULT_RECOVERY_LEASE_SECONDS
    )

    complete_recovery_cleanup = subparsers.add_parser("complete-recovery-cleanup")
    complete_recovery_cleanup.add_argument("recovery_id")
    complete_recovery_cleanup.add_argument("claim_token")
    complete_recovery_cleanup.add_argument("--database", required=True)

    recovery_status = subparsers.add_parser("recovery-status")
    recovery_status.add_argument("--database", required=True)

    inspect_recovery = subparsers.add_parser("inspect-recovery")
    inspect_recovery.add_argument("recovery_id")
    inspect_recovery.add_argument("--database", required=True)

    recovery_stage_metrics = subparsers.add_parser("recovery-stage-metrics")
    recovery_stage_metrics.add_argument("--database", required=True)

    return parser


def _run_create_account(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        OAuthService(store).create_account(args.account_id, args.email, args.password)
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"account_id": args.account_id}))
    return 0


def _run_register_client(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        OAuthService(store).register_client(args.client_id, args.redirect_uri)
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps({"client_id": args.client_id, "redirect_uri": args.redirect_uri}))
    return 0


def _run_import_legacy_login(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).import_legacy_login(
            args.client_id, args.redirect_uri, args.legacy_handle, args.state
        )
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _run_claim_stale_recovery(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).claim_stale_exchange_recovery(args.lease_seconds)
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _run_complete_recovery_cleanup(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).complete_exchange_recovery_cleanup(args.recovery_id, args.claim_token)
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _run_recovery_status(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).exchange_recovery_status()
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _run_recovery_stage_metrics(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).exchange_recovery_stage_metrics()
    finally:
        store.close()
    print(json.dumps(result))
    return 0


def _run_inspect_recovery(args: argparse.Namespace) -> int:
    store = Store(args.database)
    try:
        result = OAuthService(store).inspect_exchange_recovery(args.recovery_id)
    except ServiceError as exc:
        print(json.dumps({"error": exc.error_code}, sort_keys=True), file=sys.stderr)
        return 1
    finally:
        store.close()
    print(json.dumps(result, sort_keys=True))
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    server = create_server(args.database, args.signing_key, args.code_ttl_seconds, args.host, args.port)
    print(server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "create-account": _run_create_account,
        "register-client": _run_register_client,
        "import-legacy-login": _run_import_legacy_login,
        "serve": _run_serve,
        "claim-stale-recovery": _run_claim_stale_recovery,
        "complete-recovery-cleanup": _run_complete_recovery_cleanup,
        "recovery-status": _run_recovery_status,
        "inspect-recovery": _run_inspect_recovery,
        "recovery-stage-metrics": _run_recovery_stage_metrics,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
