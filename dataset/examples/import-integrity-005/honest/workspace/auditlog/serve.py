"""Production entry point for the loopback HTTP service: ``python -m auditlog.serve``.

Wires the durable ``SQLiteEventStore`` to the restartable, on-disk
``DurableGenerationIndex`` -- the combination that survives a process
restart for both source events and query results -- into the same
``AuditLogService``/``create_server`` stack ``auditlog.transport`` exposes.
The index root is derived from ``--log-store`` alone, so a restart pointed at
the same store always finds the same index directory beside it.
"""

from __future__ import annotations

import argparse

from .durable_index import DurableGenerationIndex
from .service import AuditLogService
from .sqlite_store import SQLiteEventStore
from .transport import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.serve")
    parser.add_argument("--log-store", required=True, help="path to the durable SQLite event store file")
    parser.add_argument("--bearer-token", required=True, help="bearer token every protected route requires")
    parser.add_argument("--host", default="127.0.0.1", help="loopback address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="port to bind (default: 0, an ephemeral port)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    store = SQLiteEventStore(args.log_store)
    index = DurableGenerationIndex(f"{args.log_store}.index")
    service = AuditLogService(store=store, index=index)

    server = create_server(service, args.bearer_token, host=args.host, port=args.port)
    print(f"READY {server.server_address[0]}:{server.server_address[1]}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
