"""Command-line shell for the audit log service.

``build_parser`` is the stable contract other tooling imports: the
``record``/``query``/``repair`` subcommands and their required
``--log-store`` option never change shape. ``main`` wires that parser to
:class:`~auditlog.service.AuditService` over a :class:`~auditlog.store.JsonFileLogStore`.

``serve`` is a separate surface: it runs the loopback-only V1 HTTP server
from :mod:`auditlog.httpd` over a :class:`~auditlog.store.SqliteLogStore`,
in the foreground, until interrupted.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from auditlog.httpd import LoopbackHostError, ensure_loopback_host, serve as run_server
from auditlog.service import ArchiveFormatError, AuditService, SequenceError
from auditlog.store import JsonFileLogStore, SqliteLogStore


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
        "serve", help="run the loopback V1 HTTP surface in the foreground"
    )
    serve.add_argument("--log-store", required=True, help="path to a SQLite log-store file")
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--metadata expects KEY=VALUE, got {pair!r}")
        key, _, value = pair.partition("=")
        metadata[key] = value
    return metadata


def _format_event(event) -> str:
    return "\t".join(
        (str(event.sequence), event.event_id, event.actor, event.action, event.outcome, event.recorded_at)
    )


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the requested command against ``--log-store``."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        try:
            ensure_loopback_host(args.host)
        except LoopbackHostError as exc:
            parser.error(str(exc))
            return 2
        run_server(SqliteLogStore(args.log_store), args.bearer_token, host=args.host, port=args.port)
        return 0

    service = AuditService(JsonFileLogStore(args.log_store))

    try:
        if args.command == "record":
            metadata = _parse_metadata(args.metadata)
            recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            event = service.record(args.actor, args.action, args.outcome, recorded_at, metadata)
            print(_format_event(event))
            return 0

        if args.command == "query":
            for event in service.query(actor=args.actor, action=args.action):
                print(_format_event(event))
            return 0

        if args.command == "repair":
            report = service.repair()
            status = "migrated" if report.migrated else "verified"
            print(f"{status} {report.verified} entries; {len(report.tampered)} tampered; index rebuilt")
            for event_id in report.tampered:
                print(f"tampered: {event_id}")
            return 1 if report.tampered else 0
    except (ValueError, SequenceError, ArchiveFormatError) as exc:
        parser.error(str(exc))

    parser.error(f"the {args.command!r} command is not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
