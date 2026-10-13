"""Command-line shell for the audit log service.

This module only parses arguments and formats output; all behavior comes
from :class:`~auditlog.service.AuditLogService`, so the CLI never touches
storage details directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .models import AuditEvent, AuditModelError
from .service import (
    AuditLogService,
    ConflictError,
    IntegrityError,
    InvalidReportPathError,
    RepairReport,
    UnsupportedOperationError,
)
from .store import JsonFileLogStore


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
        help="replay-safe key: retrying the same call with this key returns the original event",
    )
    record.add_argument("--log-store", required=True)

    query = subparsers.add_parser("query", help="read entries from the trail")
    query.add_argument("--actor")
    query.add_argument("--action")
    query.add_argument("--outcome")
    query.add_argument("--recorded-from", help="inclusive lower bound on recorded_at")
    query.add_argument("--recorded-to", help="inclusive upper bound on recorded_at")
    query.add_argument("--log-store", required=True)

    repair = subparsers.add_parser("repair", help="rebuild derived indexes")
    repair.add_argument(
        "--report-name",
        help="write a verification report beneath the store root at this caller-named path",
    )
    repair.add_argument("--expected-count", type=int, help="flag a mismatch against this count")
    repair.add_argument("--log-store", required=True)
    return parser


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise AuditModelError(f"malformed --metadata entry {pair!r}; expected KEY=VALUE")
        metadata[key] = value
    return metadata


def _event_line(event: AuditEvent) -> str:
    return json.dumps(
        {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "actor": event.actor,
            "action": event.action,
            "outcome": event.outcome,
            "recorded_at": event.recorded_at,
            "source_version": event.source_version,
            "metadata": event.metadata,
        },
        sort_keys=True,
    )


def _report_line(report: RepairReport) -> str:
    return json.dumps(
        {
            "verified_count": report.verified_count,
            "corrupted_sequences": list(report.corrupted_sequences),
            "sequence_gap_at": report.sequence_gap_at,
            "reordered_sequences": list(report.reordered_sequences),
            "count_mismatch": list(report.count_mismatch) if report.count_mismatch else None,
            "completed_imports": list(report.completed_imports),
            "is_clean": report.is_clean,
            "rebuilt_index_path": report.rebuilt_index_path,
            "report_path": report.report_path,
        },
        sort_keys=True,
    )


def _run_record(args: argparse.Namespace, service: AuditLogService, out: Any) -> int:
    metadata = _parse_metadata(args.metadata)
    event = service.record(
        args.actor,
        args.action,
        args.outcome,
        metadata=metadata,
        idempotency_key=args.idempotency_key,
    )
    print(_event_line(event), file=out)
    return 0


def _run_query(args: argparse.Namespace, service: AuditLogService, out: Any) -> int:
    events = service.query(
        actor=args.actor,
        action=args.action,
        outcome=args.outcome,
        recorded_from=args.recorded_from,
        recorded_to=args.recorded_to,
    )
    for event in events:
        print(_event_line(event), file=out)
    return 0


def _run_repair(args: argparse.Namespace, service: AuditLogService, out: Any) -> int:
    report = service.repair(report_name=args.report_name, expected_count=args.expected_count)
    print(_report_line(report), file=out)
    return 0 if report.is_clean else 1


_HANDLERS = {"record": _run_record, "query": _run_query, "repair": _run_repair}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = JsonFileLogStore(args.log_store)
    try:
        return _HANDLERS[args.command](args, service, sys.stdout)
    except AuditModelError as exc:
        parser.error(str(exc))
        return 2
    except (
        UnsupportedOperationError,
        IntegrityError,
        ConflictError,
        InvalidReportPathError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
