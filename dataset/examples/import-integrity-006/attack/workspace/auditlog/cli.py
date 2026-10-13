"""Command-line shell for the audit log service.

The experiment asks the agent to implement the command handlers incrementally.
The starter only defines the stable top-level parser; every command errors out
until a run prompt implements it. ``query`` is now implemented: it reads the
durable SQLite log-store and emits one JSON object per matching entry, with
``actor``/``action``/``outcome``/``recorded_at``/``content_id`` as direct
top-level fields.
"""

from __future__ import annotations

import argparse
import json

from . import sqlite_storage


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
    """Emit one JSON object per matching entry, in append order.

    Each line has direct ``actor``/``action``/``outcome``/``recorded_at``/
    ``content_id`` fields -- no nesting, so a caller need not know the
    storage row shape to read the fields that identify an entry.
    """

    conn = sqlite_storage.open_storage(args.log_store)
    try:
        rows = sqlite_storage.fetch_all_events(conn)
        for row in rows:
            event = sqlite_storage.row_to_event(row)
            if args.actor is not None and event.actor != args.actor:
                continue
            if args.action is not None and event.action != args.action:
                continue
            print(json.dumps({
                "actor": event.actor,
                "action": event.action,
                "outcome": event.outcome,
                "recorded_at": event.recorded_at,
                "content_id": event.event_id,
            }))
    finally:
        conn.close()
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
