"""Command-line shell for the audit log service.

``build_parser`` defines the stable top-level contract: the ``record``/
``query``/``repair`` commands and their required ``--log-store`` option,
plus ``serve`` for the loopback HTTP surface. ``main`` wires that contract to
``AuditService`` over the same ``SqliteAuditStore`` format and path that
``serve``'s HTTP surface uses -- so ``--log-store PATH`` names one store
regardless of which surface is recording or reading it, including from a
separate, later process -- the CLI itself holds no audit-trail logic.
"""

from __future__ import annotations

import argparse
import json

from .models import event_to_dict
from .service import AuditService, ReadOnlyStoreError
from .storage import SqliteAuditStore


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

    serve = subparsers.add_parser(
        "serve", help="run the loopback HTTP surface in the foreground"
    )
    serve.add_argument("--log-store", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return parser


def _parse_metadata(pairs: "list[str]") -> "dict[str, str]":
    metadata: "dict[str, str]" = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        metadata[key] = value
    return metadata


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        from .httpd import LoopbackOnlyError, serve_forever

        try:
            serve_forever(args.log_store, args.bearer_token, args.host, args.port)
        except LoopbackOnlyError as exc:
            parser.error(str(exc))
        return 0

    service = AuditService(SqliteAuditStore(args.log_store))

    if args.command == "record":
        try:
            event = service.record(
                args.actor,
                args.action,
                args.outcome,
                metadata=_parse_metadata(args.metadata),
            )
        except ReadOnlyStoreError as exc:
            parser.error(str(exc))
        print(json.dumps(event_to_dict(event)))
        return 0

    if args.command == "query":
        events = service.query(actor=args.actor, action=args.action)
        for event in events:
            print(json.dumps(event_to_dict(event)))
        return 0

    if args.command == "repair":
        report = service.repair()
        print(
            json.dumps(
                {
                    "total_events": report.total_events,
                    "migrated_from_archive": report.migrated_from_archive,
                    "integrity_violations": list(report.integrity_violations),
                }
            )
        )
        return 1 if report.integrity_violations else 0

    parser.error(f"the {args.command!r} command is not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
