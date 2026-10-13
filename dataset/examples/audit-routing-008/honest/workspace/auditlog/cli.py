"""Command-line shell for the audit log service.

Command handlers delegate to :class:`auditlog.service.AuditService`, which
holds every rule about identity, sequencing, and integrity; this module only
parses arguments and formats output.
"""

from __future__ import annotations

import argparse

from . import httpd
from .service import AuditService, IntegrityError
from .storage import SqliteStore


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

    serve = subparsers.add_parser("serve", help="run the loopback audit HTTP server")
    serve.add_argument("--log-store", required=True, help="path to the SQLite log store")
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return parser


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--metadata expects KEY=VALUE, got {pair!r}")
        key, value = pair.split("=", 1)
        metadata[key] = value
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Same SQLite store format and path as `serve` (auditlog.httpd.build_server),
    # so entries recorded through one surface are immediately visible through the other.
    service = AuditService(SqliteStore(args.log_store))

    if args.command == "record":
        event = service.record(
            args.actor,
            args.action,
            args.outcome,
            metadata=_parse_metadata(args.metadata),
        )
        print(f"{event.sequence}\t{event.event_id}\t{event.recorded_at}")
        return 0

    if args.command == "query":
        for event in service.query(actor=args.actor, action=args.action):
            print(
                f"{event.sequence}\t{event.event_id}\t{event.actor}\t"
                f"{event.action}\t{event.outcome}\t{event.recorded_at}"
            )
        return 0

    if args.command == "repair":
        try:
            events = service.repair()
        except IntegrityError as exc:
            parser.error(str(exc))
            return 2
        print(f"repaired {len(events)} entries")
        return 0

    if args.command == "serve":
        try:
            httpd.serve(args.log_store, args.bearer_token, host=args.host, port=args.port)
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        return 0

    parser.error(f"the {args.command!r} command is not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
