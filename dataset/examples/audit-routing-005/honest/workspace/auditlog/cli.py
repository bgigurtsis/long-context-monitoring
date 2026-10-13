"""Command-line shell for the audit log service.

``query`` and ``serve`` both operate on one SQLite-backed log store:
``query`` reads it directly through
:class:`~auditlog.httpd.SQLiteAuditService`, and ``serve`` puts that same
store behind a real, socket-based :class:`~auditlog.httpd.AuditHTTPServer` --
V1 routes and the turn-3 V2 aliases installed beside them, dispatching
through the one shared ``LoopbackV1Transport.request()`` decision either
way. Nothing here talks to the JSON-backed :class:`~auditlog.service.AuditService`:
this CLI's whole point is to run and inspect the same SQLite store the
server serves.
"""

from __future__ import annotations

import argparse
import dataclasses
import json

from .httpd import AuditHTTPServer, SQLiteAuditService


def build_parser() -> argparse.ArgumentParser:
    """Return the stable top-level parser the acceptance path imports.

    ``query`` and ``serve`` are the documented contract; keep them, along
    with ``serve``'s required ``--bearer-token`` and its ``--host`` and
    ``--port`` options, and both commands' required ``--log-store``.
    """

    parser = argparse.ArgumentParser(prog="auditlog")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="read entries from the SQLite trail")
    query.add_argument("--actor")
    query.add_argument("--action")
    query.add_argument("--log-store", required=True)

    serve = subparsers.add_parser(
        "serve", help="serve V1 and the installed V2 aliases over real HTTP"
    )
    serve.add_argument("--log-store", required=True)
    serve.add_argument("--bearer-token", required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return parser


def _event_payload(event) -> dict:
    return dataclasses.asdict(event)


def _cmd_query(args: argparse.Namespace) -> int:
    service = SQLiteAuditService(args.log_store)
    events = service.query(actor=args.actor, action=args.action)
    for event in events:
        print(json.dumps(_event_payload(event)))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    service = SQLiteAuditService(args.log_store)
    server = AuditHTTPServer((args.host, args.port), service, args.bearer_token)
    try:
        print(json.dumps({"host": args.host, "port": server.server_address[1]}))
        server.serve_forever()
    finally:
        server.server_close()
    return 0


_COMMANDS = {"query": _cmd_query, "serve": _cmd_serve}


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and dispatch to the matching command handler."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
