"""Run the loopback audit service as a real OS process.

    python -m auditlog.serve --log-store STORE.db --bearer-token TOKEN \\
        [--host 127.0.0.1] [--port 0]

Backed by ``SQLiteAuditLogService``, the production storage implementation
the CLI and HTTP surfaces are meant to share. Prints the bound host and port
once listening starts, so a caller that asked for an OS-assigned port
(``--port 0``) can discover it from this process's stdout.
"""

from __future__ import annotations

import argparse

from auditlog.http_transport import create_server
from auditlog.sqlite_store import SQLiteAuditLogService


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

    service = SQLiteAuditLogService(args.log_store)
    server = create_server(service, args.bearer_token, host=args.host, port=args.port)
    host, port = server.server_address
    print(f"listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
