"""Command-line shell for the audit log service.

Each command is a thin adapter onto ``auditlog.service``: the CLI parses
arguments and formats output, and the service functions carry all of the
storage-independent behavior (identity, sequencing, integrity, repair).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .httpd import create_server
from .service import LogStoreError, open_store, query_events, record_event
from .timeutil import now_utc


def build_parser() -> argparse.ArgumentParser:
    """Return the stable top-level parser the acceptance path imports.

    The ``record``/``query``/``repair`` commands and their required
    ``--log-store`` option are the documented contract; keep them. ``serve``
    exposes the same loopback server ``auditlog.httpd.create_server`` builds
    (bearer-protected V1 routes plus the installed V2 aliases) and reads
    from and writes to that same ``--log-store`` path and format, so a
    ``query`` run afterward against the same path sees what ``serve``
    recorded.
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
        "serve", help="run the loopback HTTP server (V1 routes plus installed V2 aliases)"
    )
    serve.add_argument("--log-store", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    return parser


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    """Turn repeated ``KEY=VALUE`` options into the metadata dict callers see."""

    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"--metadata expects KEY=VALUE, got {pair!r}")
        metadata[key] = value
    return metadata


def _run_record(args: argparse.Namespace) -> int:
    store = open_store(Path(args.log_store))
    event = record_event(
        store,
        actor=args.actor,
        action=args.action,
        outcome=args.outcome,
        recorded_at=now_utc(),
        metadata=_parse_metadata(args.metadata),
    )
    print(json.dumps(event.to_record()))
    return 0


def _run_query(args: argparse.Namespace) -> int:
    store = open_store(Path(args.log_store))
    for event in query_events(store, actor=args.actor, action=args.action):
        print(json.dumps(event.to_record()))
    return 0


def _run_repair(args: argparse.Namespace) -> int:
    store = open_store(Path(args.log_store))
    report = store.repair()
    print(
        json.dumps(
            {
                "event_count": report.event_count,
                "resequenced": report.resequenced,
                "migrated_from_archive": report.migrated_from_archive,
            }
        )
    )
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    server = create_server(
        Path(args.log_store), args.bearer_token, host=args.host, port=args.port
    )
    print(json.dumps({"host": server.server_address[0], "port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


_HANDLERS = {
    "record": _run_record,
    "query": _run_query,
    "repair": _run_repair,
    "serve": _run_serve,
}


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch to the matching command handler."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _HANDLERS[args.command](args)
    except (LogStoreError, ValueError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
