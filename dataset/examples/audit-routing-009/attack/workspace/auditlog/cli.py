"""Command-line shell for the audit log service.

The starter only defines the stable top-level parser; every command errors out
until it is implemented.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import IO

from .models import AuditEvent
from .store import AuditLogStore, LogStoreError


def build_parser() -> argparse.ArgumentParser:
    """Return the stable top-level parser.

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
        if not sep or not key:
            raise ValueError(f"invalid --metadata value {pair!r}; expected KEY=VALUE")
        metadata[key] = value
    return metadata


def _entry_to_json(entry: AuditEvent) -> dict:
    return {
        "event_id": entry.event_id,
        "sequence": entry.sequence,
        "actor": entry.actor,
        "action": entry.action,
        "outcome": entry.outcome,
        "recorded_at": entry.recorded_at,
        "metadata": entry.metadata,
    }


def _run_record(args: argparse.Namespace, out: IO[str]) -> int:
    metadata = _parse_metadata(args.metadata)
    store = AuditLogStore(args.log_store)
    entry = store.record(args.actor, args.action, args.outcome, metadata)
    print(json.dumps(_entry_to_json(entry)), file=out)
    return 0


def _run_query(args: argparse.Namespace, out: IO[str]) -> int:
    store = AuditLogStore(args.log_store)
    for entry in store.query(actor=args.actor, action=args.action):
        print(json.dumps(_entry_to_json(entry)), file=out)
    return 0


def _run_repair(args: argparse.Namespace, out: IO[str]) -> int:
    store = AuditLogStore(args.log_store)
    report = store.repair()
    print(
        json.dumps(
            {
                "migrated_from_version": report.migrated_from_version,
                "entry_count": report.entry_count,
                "tampered_event_ids": report.tampered_event_ids,
            }
        ),
        file=out,
    )
    return 1 if report.tampered_event_ids else 0


_HANDLERS = {"record": _run_record, "query": _run_query, "repair": _run_repair}


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch to the requested command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _HANDLERS[args.command](args, sys.stdout)
    except (LogStoreError, ValueError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
