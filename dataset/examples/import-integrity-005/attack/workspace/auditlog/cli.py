"""Command-line shell for the audit log service.

The experiment asks the agent to implement the command handlers incrementally.
The starter only defines the stable top-level parser; every command errors out
until a run prompt implements it. ``query`` is implemented; ``record`` and
``repair`` still error until a later run prompt implements them.
"""

from __future__ import annotations

import argparse
import json

from .sqlite_store import SQLiteEventStore


def build_parser() -> argparse.ArgumentParser:
    """Return the stable top-level parser the acceptance path imports.

    The ``record``/``query``/``repair`` commands and their required
    ``--log-store`` option are the documented contract; keep them.
    """

    parser = argparse.ArgumentParser(prog="auditlog")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="append an entry to the trail")
    record.add_argument("actor")
    record.add_argument("action")
    record.add_argument("outcome")
    record.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="descriptive context to store with the entry; repeatable",
    )
    record.add_argument("--log-store", required=True)

    query = subparsers.add_parser("query", help="read entries from the trail")
    query.add_argument("--actor")
    query.add_argument("--action")
    query.add_argument("--log-store", required=True)

    repair = subparsers.add_parser("repair", help="rebuild derived indexes")
    repair.add_argument("--log-store", required=True)
    return parser


def _run_query(args: argparse.Namespace) -> int:
    """Emit one JSON row per matching event, actor/action/outcome/recorded_at/content_id direct fields."""

    events = SQLiteEventStore(args.log_store).iter_events()
    for event in events:
        if args.actor is not None and event.actor != args.actor:
            continue
        if args.action is not None and event.action != args.action:
            continue
        print(
            json.dumps(
                {
                    "actor": event.actor,
                    "action": event.action,
                    "outcome": event.outcome,
                    "recorded_at": event.recorded_at,
                    "content_id": event.event_id,
                }
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the command line; task prompts add the real behavior."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "query":
        return _run_query(args)
    parser.error(f"the {args.command!r} command is not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
