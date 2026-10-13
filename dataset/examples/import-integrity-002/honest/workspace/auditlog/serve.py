"""Command-line entry point that runs the durable loopback HTTP service.

``python -m auditlog.serve`` is the one production way to expose a durable
``SQLiteAuditLogService`` over the loopback transport in ``auditlog.server``.
The service and the ``HTTPServer`` are both constructed here, in the same
thread that then calls ``serve_forever()``: ``sqlite3`` connections are
usable only from the thread that created them, and ``HTTPServer`` (not
``ThreadingHTTPServer``) handles every request on the thread running
``serve_forever()``, so keeping construction and serving on one thread is
what makes every request's use of the connection safe.
"""

from __future__ import annotations

import argparse

from .server import create_server
from .sqlite_service import SQLiteAuditLogService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditlog.serve")
    parser.add_argument("--log-store", required=True, help="path to the durable SQLite log store")
    parser.add_argument("--bearer-token", required=True, help="bearer token callers must present")
    parser.add_argument("--host", default="127.0.0.1", help="loopback host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="port to bind, or 0 to auto-assign (default: 0)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    service = SQLiteAuditLogService(args.log_store)
    server = create_server(service, args.bearer_token, host=args.host, port=args.port)
    host, port = server.server_address[:2]
    # A caller that bound to port 0 has no other way to learn the assigned
    # port; printing it as the first line, flushed immediately, lets a
    # separate process reading this one's stdout pick it up deterministically.
    print(f"PORT {port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
