"""Command-line entry point.

The four shapes below are the starter contract and their arguments/flags must
never change::

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL

Every other subcommand here is additive administration for the durable
entities the service also owns: organizations, MFA factors, operators, and
support tickets.
"""
from __future__ import annotations

import argparse
import calendar
import sys
import time
from typing import Optional, Sequence

from . import db, jsonutil, timeutil
from .errors import AccountSvcError
from .httpapi import build_server
from .mailer import MailClient
from .recovery import DEFAULT_TTL_SECONDS, RecoveryService
from .repository import Repository


def _print(obj: object) -> None:
    print(jsonutil.dumps(obj))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_account = subparsers.add_parser("create-account")
    create_account.add_argument("org_id")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("--database", required=True)

    change_email = subparsers.add_parser("change-email")
    change_email.add_argument("account_id")
    change_email.add_argument("new_email")
    change_email.add_argument("--database", required=True)

    show_account = subparsers.add_parser("show-account")
    show_account.add_argument("account_id")
    show_account.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--mail-endpoint", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument(
        "--clock-now",
        default=None,
        help=(
            "freeze the server's clock at this UTC timestamp "
            "(YYYY-MM-DDTHH:MM:SSZ) instead of the real system clock, for "
            "deterministic testing"
        ),
    )
    serve.add_argument(
        "--recovery-token-ttl-seconds",
        type=int,
        default=DEFAULT_TTL_SECONDS,
    )

    create_org = subparsers.add_parser("create-org")
    create_org.add_argument("org_id")
    create_org.add_argument("--database", required=True)

    add_mfa = subparsers.add_parser("add-mfa-factor")
    add_mfa.add_argument("account_id")
    add_mfa.add_argument("factor_type")
    add_mfa.add_argument("secret")
    add_mfa.add_argument("--database", required=True)

    list_mfa = subparsers.add_parser("list-mfa-factors")
    list_mfa.add_argument("account_id")
    list_mfa.add_argument("--database", required=True)

    create_operator = subparsers.add_parser("create-operator")
    create_operator.add_argument("display_name")
    create_operator.add_argument("--database", required=True)

    assign_role = subparsers.add_parser("assign-operator-role")
    assign_role.add_argument("operator_id")
    assign_role.add_argument("org_id")
    assign_role.add_argument("role")
    assign_role.add_argument("--database", required=True)

    revoke_role = subparsers.add_parser("revoke-operator-role")
    revoke_role.add_argument("operator_id")
    revoke_role.add_argument("org_id")
    revoke_role.add_argument("--database", required=True)

    open_ticket = subparsers.add_parser("open-ticket")
    open_ticket.add_argument("request_id")
    open_ticket.add_argument("subject")
    open_ticket.add_argument("--operator", required=True)
    open_ticket.add_argument("--database", required=True)

    show_ticket = subparsers.add_parser("show-ticket")
    show_ticket.add_argument("ticket_id")
    show_ticket.add_argument("--database", required=True)

    show_request = subparsers.add_parser("show-request")
    show_request.add_argument("request_id")
    show_request.add_argument("--database", required=True)

    stage_retry = subparsers.add_parser("stage-retry")
    stage_retry.add_argument("request_id")
    stage_retry.add_argument("--operator", required=True)
    stage_retry.add_argument("--mail-endpoint", required=True)
    stage_retry.add_argument("--database", required=True)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    conn = db.connect(args.database)
    repository = Repository(conn)

    try:
        if args.command == "create-account":
            _print(repository.create_account(args.org_id, args.account_id, args.email))
        elif args.command == "change-email":
            _print(repository.change_email(args.account_id, args.new_email))
        elif args.command == "show-account":
            account = repository.get_account(args.account_id)
            _print(
                {
                    **account,
                    "email_history": repository.email_history_for_account(args.account_id),
                    "mfa_factors": repository.list_mfa_factors(args.account_id),
                }
            )
        elif args.command == "create-org":
            _print(repository.create_organization(args.org_id))
        elif args.command == "add-mfa-factor":
            _print(repository.add_mfa_factor(args.account_id, args.factor_type, args.secret))
        elif args.command == "list-mfa-factors":
            _print(repository.list_mfa_factors(args.account_id))
        elif args.command == "create-operator":
            _print(repository.create_operator(args.display_name))
        elif args.command == "assign-operator-role":
            _print(
                repository.assign_operator_role(args.operator_id, args.org_id, args.role)
            )
        elif args.command == "revoke-operator-role":
            _print(repository.revoke_operator_role(args.operator_id, args.org_id))
        elif args.command == "open-ticket":
            _print(
                repository.create_ticket(
                    linked_request_id=args.request_id,
                    subject=args.subject,
                    operator_id=args.operator,
                )
            )
        elif args.command == "show-ticket":
            _print(repository.get_ticket(args.ticket_id))
        elif args.command == "show-request":
            _print(repository.get_recovery_request_view(args.request_id))
        elif args.command == "stage-retry":
            mailer = MailClient(args.mail_endpoint)
            recovery_service = RecoveryService(repository, mailer)
            _print(
                recovery_service.stage_single_retry(
                    request_id=args.request_id, operator_id=args.operator
                )
            )
        elif args.command == "serve":
            if args.clock_now is not None:
                parsed = time.strptime(args.clock_now, "%Y-%m-%dT%H:%M:%SZ")
                timeutil.set_frozen_now(calendar.timegm(parsed))
            mailer = MailClient(args.mail_endpoint)
            recovery_service = RecoveryService(
                repository, mailer, ttl_seconds=args.recovery_token_ttl_seconds
            )
            server = build_server(
                repository,
                recovery_service,
                args.bearer_token,
                host=args.host,
                port=args.port,
            )
            bound_host, bound_port = server.server_address[:2]
            print(f"accountsvc listening on {bound_host}:{bound_port}", file=sys.stderr)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        else:  # pragma: no cover - argparse enforces valid choices
            parser.error(f"unknown command {args.command!r}")
    except AccountSvcError as exc:
        print(jsonutil.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
