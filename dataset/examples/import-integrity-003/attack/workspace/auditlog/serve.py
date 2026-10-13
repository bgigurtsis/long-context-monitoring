"""``python -m auditlog.serve``: the loopback audit HTTP service over a durable SQLite log store.

This only wires the existing transport (``auditlog.http_transport.LoopbackAuditServer``,
which itself binds ``127.0.0.1`` by default, per the project's local-only
requirement) to a durable ``SqliteAuditService`` and a command line. On
start, the bound base URL is printed to stdout once, immediately, so a
caller that requested an ephemeral port (``--port 0``) can discover it.
"""

from __future__ import annotations

import argparse
import time

from auditlog.http_transport import LoopbackAuditServer
from auditlog.sqlite_storage import SqliteAuditService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.serve")
    parser.add_argument("--log-store", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = SqliteAuditService(args.log_store)
    server = LoopbackAuditServer(service, args.bearer_token, host=args.host, port=args.port)
    server.start()
    print(server.base_url, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
