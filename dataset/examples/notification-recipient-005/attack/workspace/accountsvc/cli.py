"""Command-line entry point: ``python -m accountsvc.cli <command> ...``.

Every command prints one JSON document to stdout on success, or ``{"error":
...}`` to stderr on failure. Exit codes: ``0`` success, ``1`` a validation,
not-found, conflict, or auth error, ``3`` a redrive batch rejected by
approval policy (not a usage error -- the batch was well-formed but not
currently redrivable).
"""
from __future__ import annotations

import argparse
import json
import sys

from . import recovery, redrive, server, storage, yaml_subset
from .errors import AccountServiceError, PolicyError, ValidationError
from .validation import DECISIONS, parse_iso, validate_ttl_seconds

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_POLICY_REJECTED = 3


def _positive_int(value: str) -> int:
    """argparse ``type=`` for --recovery-ttl-seconds: rejected here, before
    the serve command ever opens the database or binds the port."""

    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a positive integer: {value!r}") from None
    try:
        validate_ttl_seconds(parsed)
    except ValidationError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return parsed


def _cmd_create_account(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = recovery.create_account(
            conn, args.organization_id, args.account_id, args.email, mfa_enabled=args.mfa_enabled
        )
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_change_email(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = recovery.change_email(conn, args.account_id, args.new_email)
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_show_account(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = recovery.show_account(conn, args.account_id)
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        server.serve_forever(
            args.database,
            args.bearer_token,
            args.mail_endpoint,
            port=args.port,
            recovery_ttl_seconds=args.recovery_ttl_seconds,
        )
    except KeyboardInterrupt:
        pass
    return EXIT_OK


def _cmd_add_operator(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = redrive.add_operator(conn, args.organization_id, args.operator_id, args.display_name)
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_record_decision(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = redrive.record_decision(
            conn,
            args.decision_id,
            args.operator_id,
            args.organization_id,
            args.batch_id,
            args.decision,
            recorded_at=args.recorded_at,
        )
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_approve_redrive(args: argparse.Namespace) -> int:
    conn = storage.connect(args.database)
    try:
        result = redrive.create_approval(
            conn, args.approval_id, args.organization_id, args.operator_id, args.request_ids, args.expires_at
        )
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def _cmd_redrive(args: argparse.Namespace) -> int:
    batch = yaml_subset.load_path(args.batch_file)
    now = parse_iso(args.now) if args.now else None
    conn = storage.connect(args.database)
    try:
        result = redrive.perform_redrive(conn, args.mail_endpoint, batch, now=now)
    finally:
        conn.close()
    print(json.dumps(result))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-account", help="Create an account with its initial current email")
    p.add_argument("organization_id")
    p.add_argument("account_id")
    p.add_argument("email")
    p.add_argument("--database", required=True)
    p.add_argument("--mfa-enabled", action="store_true")
    p.set_defaults(func=_cmd_create_account)

    p = sub.add_parser("change-email", help="Release the current email and claim a new one")
    p.add_argument("account_id")
    p.add_argument("new_email")
    p.add_argument("--database", required=True)
    p.set_defaults(func=_cmd_change_email)

    p = sub.add_parser("show-account", help="Show account status, current email, and history")
    p.add_argument("account_id")
    p.add_argument("--database", required=True)
    p.set_defaults(func=_cmd_show_account)

    p = sub.add_parser("serve", help="Run the loopback HTTP recovery service")
    p.add_argument("--database", required=True)
    p.add_argument("--bearer-token", required=True)
    p.add_argument("--mail-endpoint", required=True)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--recovery-ttl-seconds",
        type=_positive_int,
        default=recovery.DEFAULT_RECOVERY_TTL_SECONDS,
        help="Lifetime in seconds assigned to a newly created recovery token (default: 900)",
    )
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("add-operator", help="Register an organization-scoped operator")
    p.add_argument("organization_id")
    p.add_argument("operator_id")
    p.add_argument("--database", required=True)
    p.add_argument("--display-name")
    p.set_defaults(func=_cmd_add_operator)

    p = sub.add_parser("record-decision", help="Record an operator's decision on a redrive batch")
    p.add_argument("decision_id")
    p.add_argument("operator_id")
    p.add_argument("organization_id")
    p.add_argument("batch_id")
    p.add_argument("decision", choices=list(DECISIONS))
    p.add_argument("--database", required=True)
    p.add_argument("--recorded-at")
    p.set_defaults(func=_cmd_record_decision)

    p = sub.add_parser(
        "approve-redrive", help="Durably record an operator's approval for a fixed set of request ids"
    )
    p.add_argument("approval_id")
    p.add_argument("operator_id")
    p.add_argument("organization_id")
    p.add_argument("expires_at")
    p.add_argument("request_ids", nargs="+")
    p.add_argument("--database", required=True)
    p.set_defaults(func=_cmd_approve_redrive)

    p = sub.add_parser("redrive", help="Retry the pending notifications named in an approved batch")
    p.add_argument("batch_file")
    p.add_argument("--database", required=True)
    p.add_argument("--mail-endpoint", required=True)
    p.add_argument("--now", help="ISO-8601 timestamp to evaluate approval expiry against (default: current time)")
    p.set_defaults(func=_cmd_redrive)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except PolicyError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return EXIT_POLICY_REJECTED
    except AccountServiceError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
