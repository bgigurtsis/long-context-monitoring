"""Command-line entry point.

    python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
    python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
    python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
    python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL

Every successful command prints one JSON object with sorted keys to stdout,
so separate invocations -- even from separate processes -- produce
byte-identical output for the same durable state.
"""
from __future__ import annotations

import json
import sys
from typing import List, Optional

from . import service
from .errors import AccountSvcError
from .httpserver import run_server
from .parser import parse_args
from .storage import Storage


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.command == "serve":
        run_server(
            database_path=args.database,
            bearer_token=args.bearer_token,
            mail_endpoint=args.mail_endpoint,
            host=args.host,
            port=args.port,
        )
        return 0

    storage = Storage(args.database)
    try:
        if args.command == "create-account":
            result = service.create_account(storage, args.org_id, args.account_id, args.email)
        elif args.command == "change-email":
            result = service.change_email(storage, args.account_id, args.new_email)
        elif args.command == "show-account":
            result = service.show_account(storage, args.account_id)
        else:  # pragma: no cover - argparse guarantees a known command
            raise AccountSvcError(f"unknown command '{args.command}'")
    except AccountSvcError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
