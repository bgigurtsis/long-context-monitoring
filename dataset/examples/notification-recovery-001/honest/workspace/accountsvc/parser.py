"""Argument parsing for the accountsvc CLI, kept separate for direct testing.

Preserves the documented CLI shapes:

    create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    show-account ACCOUNT_ID --database STATE.db
    serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL
"""
from __future__ import annotations

import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m accountsvc.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_account = subparsers.add_parser(
        "create-account", help="Create an account in an organization"
    )
    create_account.add_argument("org_id")
    create_account.add_argument("account_id")
    create_account.add_argument("email")
    create_account.add_argument("--database", required=True)

    change_email = subparsers.add_parser(
        "change-email", help="Change an account's current email"
    )
    change_email.add_argument("account_id")
    change_email.add_argument("new_email")
    change_email.add_argument("--database", required=True)

    show_account = subparsers.add_parser("show-account", help="Show an account")
    show_account.add_argument("account_id")
    show_account.add_argument("--database", required=True)

    serve = subparsers.add_parser("serve", help="Run the loopback HTTP service")
    serve.add_argument("--database", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--mail-endpoint", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)
