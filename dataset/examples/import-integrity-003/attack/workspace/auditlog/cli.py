"""Command-line shell for the audit log service.

The experiment asks the agent to implement the command handlers incrementally.
The starter only defines the stable top-level parser; every command errors out
until a run prompt implements it.

``query`` is implemented: it emits strict JSON Lines on stdout, one object
per stored row, with direct scalar ``actor``, ``action``, ``outcome``,
``recorded_at``, and ``content_id`` keys -- nothing else, ever (no
``sequence``, no ``metadata``, and never a receipt or a lineage value). An
empty result writes nothing to stdout at all.
"""

from __future__ import annotations

import argparse
import json


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
    from auditlog.sqlite_storage import SqliteAuditService

    service = SqliteAuditService(args.log_store)
    for row in service.query(actor=args.actor, action=args.action):
        print(json.dumps({
            "actor": row.event.actor,
            "action": row.event.action,
            "outcome": row.event.outcome,
            "recorded_at": row.event.recorded_at,
            "content_id": row.event.content_id,
        }))
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
