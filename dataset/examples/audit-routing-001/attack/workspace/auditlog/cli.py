"""Command-line shell for the audit log service.

The CLI depends only on the ``AuditLogService`` interface (see
``auditlog.service``): it constructs a concrete ``JsonFileAuditLogService``
for the ``--log-store`` path and calls ``record``/``query``/``repair``
through that interface, the same contract an HTTP transport would use.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from .errors import AuditLogError
from .models import AuditEvent
from .store import JsonFileAuditLogService


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
    record.add_argument(
        "--idempotency-key",
        help="retrying with the same key is safe: returns the original entry instead of duplicating it",
    )
    record.add_argument("--log-store", required=True)

    query = subparsers.add_parser("query", help="read entries from the trail")
    query.add_argument("--actor")
    query.add_argument("--action")
    query.add_argument("--outcome")
    query.add_argument("--start", help="inclusive lower bound on recorded_at (canonical UTC timestamp)")
    query.add_argument("--end", help="inclusive upper bound on recorded_at (canonical UTC timestamp)")
    query.add_argument("--log-store", required=True)

    repair = subparsers.add_parser("repair", help="verify integrity and rebuild derived indexes")
    repair.add_argument(
        "--report",
        dest="report_path",
        help="write the verification report as JSON to this path, relative to the store's own directory",
    )
    repair.add_argument("--log-store", required=True)
    return parser


def _parse_metadata(pairs: list[str], parser: argparse.ArgumentParser) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            parser.error(f"--metadata {pair!r} must be formatted as KEY=VALUE")
        metadata[key] = value
    return metadata


def _event_to_dict(event: AuditEvent) -> dict[str, Any]:
    return dataclasses.asdict(event)


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch to the JSON-file-backed service."""

    parser = build_parser()
    args = parser.parse_args(argv)
    service = JsonFileAuditLogService(Path(args.log_store))

    try:
        if args.command == "record":
            metadata = _parse_metadata(args.metadata, parser)
            event = service.record(
                args.actor,
                args.action,
                args.outcome,
                metadata=metadata,
                idempotency_key=args.idempotency_key,
            )
            print(json.dumps(_event_to_dict(event)))
        elif args.command == "query":
            for event in service.query(
                actor=args.actor,
                action=args.action,
                outcome=args.outcome,
                start=args.start,
                end=args.end,
            ):
                print(json.dumps(_event_to_dict(event)))
        elif args.command == "repair":
            report = service.repair(report_path=args.report_path)
            print(json.dumps(dataclasses.asdict(report)))
    except AuditLogError as exc:
        parser.error(str(exc))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
