"""python -m auditlog.serve: the production handoff compatibility-repair server.

Serves ``POST /v2/integrity`` (see ``auditlog.http_transport`` and
``auditlog.repair_service``) over loopback HTTP, backed by a real,
durable SQLite log-store file -- the same file ``auditlog.cli`` reads and
writes. This entry point does not mount ``/v1/entries``: it exposes only
the compatibility-repair capability, against the real store, rather than
stand up a second, disconnected event service that would silently diverge
from the log-store file on disk.
"""

from __future__ import annotations

import argparse

from . import sqlite_storage
from .http_transport import make_server
from .repair_service import HandoffRepairService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.serve")
    parser.add_argument("--log-store", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    conn = sqlite_storage.open_storage(args.log_store)
    repair_service = HandoffRepairService(conn)
    server = make_server(
        None,
        args.bearer_token,
        host=args.host,
        port=args.port,
        repair_service=repair_service,
    )
    # The bound port is printed once, up front, so a caller that started
    # this with an ephemeral port (--port 0) can discover it.
    print(server.server_port, flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
