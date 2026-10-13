"""Command-line shell for the audit log service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auditlog.service import AuditLogService, IntegrityError, SequenceError
from auditlog.storage import ReadOnlyStoreError, open_store


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


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"--metadata expects KEY=VALUE, got {pair!r}")
        metadata[key] = value
    return metadata


def _print_event(event) -> None:
    print(
        json.dumps(
            {
                "event_id": event.event_id,
                "sequence": event.sequence,
                "actor": event.actor,
                "action": event.action,
                "outcome": event.outcome,
                "recorded_at": event.recorded_at,
                "source_version": event.source_version,
                "metadata": event.metadata,
            }
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the requested command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    service = AuditLogService(open_store(Path(args.log_store)))

    if args.command == "record":
        try:
            metadata = _parse_metadata(args.metadata)
        except ValueError as exc:
            parser.error(str(exc))
        try:
            event = service.record(args.actor, args.action, args.outcome, metadata)
        except ReadOnlyStoreError as exc:
            parser.error(str(exc))
        _print_event(event)
        return 0

    if args.command == "query":
        for event in service.query(actor=args.actor, action=args.action):
            _print_event(event)
        return 0

    if args.command == "repair":
        try:
            events = service.verify()
        except (SequenceError, IntegrityError) as exc:
            print(f"repair: trail is broken: {exc}", file=sys.stderr)
            return 1
        print(f"repair: {len(events)} entries verified, trail intact")
        return 0

    parser.error(f"the {args.command!r} command is not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
