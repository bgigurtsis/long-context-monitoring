"""Command-line shell for the audit log service.

The CLI is a thin caller of ``auditlog.service.AuditService``: it parses
arguments, builds a ``SqliteLogStore`` for ``--log-store``, and prints results
as JSON. All of the actual record/query/repair behavior -- identity, gapless
sequencing, immutability -- lives in the service and store layers, not here.

``serve`` and ``query`` are kept on that one durable store format and the
same ``--log-store`` path on purpose: ``serve`` hands the path straight to
``auditlog.httpd.serve``, which durably backs the HTTP service with
``SqliteLogStore`` too, so a record made over loopback HTTP by one process is
visible to ``query`` run fresh in another process against the same path.
"""

from __future__ import annotations

import argparse
import json

from . import httpd
from .models import AuditEvent
from .service import AuditService
from .store import IntegrityError, SqliteLogStore


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

    serve = subparsers.add_parser("serve", help="serve the audit log over loopback HTTP")
    serve.add_argument("--log-store", required=True)
    serve.add_argument(
        "--bearer-token",
        action="append",
        default=[],
        required=True,
        metavar="TOKEN",
        help="accepted bearer token; repeatable",
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return parser


def _parse_metadata(pairs: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise ValueError(f"invalid --metadata value {pair!r}, expected KEY=VALUE")
        metadata[key] = value
    return metadata


def _event_to_dict(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


def _run_record(service: AuditService, args: argparse.Namespace) -> int:
    metadata = _parse_metadata(args.metadata)
    event = service.record(args.actor, args.action, args.outcome, metadata=metadata)
    print(json.dumps(_event_to_dict(event), sort_keys=True))
    return 0


def _run_query(service: AuditService, args: argparse.Namespace) -> int:
    events = service.query(actor=args.actor, action=args.action)
    for event in events:
        print(json.dumps(_event_to_dict(event), sort_keys=True))
    return 0


def _run_repair(service: AuditService, args: argparse.Namespace) -> int:
    report = service.repair()
    print(json.dumps({"entries_checked": report.entries_checked, "index_rebuilt": report.index_rebuilt}, sort_keys=True))
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    httpd.serve(args.log_store, frozenset(args.bearer_token), host=args.host, port=args.port)
    return 0


_HANDLERS = {"record": _run_record, "query": _run_query, "repair": _run_repair}


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch to the matching handler.

    ``serve`` is handled separately from ``record``/``query``/``repair``: it
    does not build its own ``AuditService`` here -- ``auditlog.httpd.serve``
    builds one internally, backed by the same ``SqliteLogStore`` format the
    other commands use against ``--log-store``.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _run_serve(args)
    service = AuditService(SqliteLogStore(args.log_store))
    try:
        return _HANDLERS[args.command](service, args)
    except IntegrityError as exc:
        parser.exit(1, f"auditlog: {exc}\n")
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
